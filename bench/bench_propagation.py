"""Phase 0 計算予算実測ベンチマーク (PHASES.md 作業項目5 / 出口条件「計算予算実測メモ」)

これは物理エンジンではなくコストモデルの実測装置である。
1実現 = カタログ全星を誤差からリサンプル → ±窓で伝播 → 太陽への最接近を検出。
このコストを (カタログ規模 N) × (時間刻み dt) の格子で測り、
workers=6 プロセス並列のスケーリングを実測する (憲法第2条4項の実測則の更新)。

伝播の内容は主経路 (軸対称ポテンシャル内のリープフロッグ軌道積分,
MWPotential2014 級の 3 成分: Miyamoto-Nagai 円盤 + Hernquist バルジ + NFW ハロー)
と同等の flop 構成で、コスト実測として本番と同じスケーリングを持つ。

単位系: kpc / Myr / Msun。 1 km/s = 1.0227e-3 kpc/Myr。
"""

import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor

G = 4.49850e-12  # kpc^3 / (Msun Myr^2)
KMS = 1.02271e-3  # km/s -> kpc/Myr

# MWPotential2014 級の3成分 (コスト実測用の代表値)
MN_M, MN_A, MN_B = 6.8e10, 3.0, 0.28          # Miyamoto-Nagai 円盤
HQ_M, HQ_A = 0.5e10, 0.5                      # Hernquist バルジ
NFW_M, NFW_RS = 8.0e11, 16.0                  # NFW ハロー

R0 = 8.122       # 太陽の銀河中心距離 kpc
VC0 = 236 * KMS  # 円速度近似 kpc/Myr


def accel(pos):
    """軸対称3成分ポテンシャルの加速度。pos: (N,3) kpc → (N,3) kpc/Myr^2"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    R2 = x * x + y * y
    r = np.sqrt(R2 + z * z)
    # Miyamoto-Nagai
    zb = np.sqrt(z * z + MN_B * MN_B)
    azb = MN_A + zb
    denom = np.power(R2 + azb * azb, 1.5)
    ax = -G * MN_M * x / denom
    ay = -G * MN_M * y / denom
    az = -G * MN_M * z * azb / (zb * denom)
    # Hernquist
    fac = G * HQ_M / ((r + HQ_A) ** 2 * np.maximum(r, 1e-12))
    ax -= fac * x
    ay -= fac * y
    az -= fac * z
    # NFW
    xr = r / NFW_RS
    mr = np.log1p(xr) - xr / (1.0 + xr)
    fac = G * NFW_M * mr / np.maximum(r, 1e-12) ** 3
    ax -= fac * x
    ay -= fac * y
    az -= fac * z
    return np.stack([ax, ay, az], axis=1)


def make_catalog(n, rng):
    """太陽近傍の模擬カタログ (LSR 周り、分散 ~30 km/s、半径 ~0.3 kpc の球)"""
    pos_local = rng.normal(0.0, 0.15, (n, 3))
    sun = np.array([R0, 0.0, 0.0208])
    pos = pos_local + sun
    vel = rng.normal(0.0, 30 * KMS, (n, 3))
    vel[:, 1] += VC0  # 銀河回転
    return pos, vel


def sun_state():
    pos = np.array([[R0, 0.0, 0.0208]])
    vel = np.array([[11.1 * KMS, VC0 + 12.24 * KMS, 7.25 * KMS]])
    return pos, vel


def propagate_leapfrog(pos, vel, t_end, dt):
    """全星 + 太陽を一括リープフロッグ積分し、太陽への最接近距離/時刻を返す。
    軌道は保存せず、ステップごとに min 距離を更新 (本番と同じメモリ設計)。"""
    sp, sv = sun_state()
    P = np.vstack([sp, pos]).copy()
    V = np.vstack([sv, vel]).copy()
    sign = 1.0 if t_end > 0 else -1.0
    h = sign * dt
    nstep = int(round(abs(t_end) / dt))
    dmin = np.full(P.shape[0] - 1, np.inf)
    tmin = np.zeros(P.shape[0] - 1)
    a = accel(P)
    t = 0.0
    for _ in range(nstep):
        V += 0.5 * h * a
        P += h * V
        a = accel(P)
        V += 0.5 * h * a
        t += h
        d = np.linalg.norm(P[1:] - P[0], axis=1)
        closer = d < dmin
        dmin[closer] = d[closer]
        tmin[closer] = t
    return dmin, tmin


def propagate_linear(pos, vel, t_end, dt):
    """線形伝播 (LMA)。閉形式で最接近を解く。コスト比較用。"""
    sp, sv = sun_state()
    dp = pos - sp
    dv = vel - sv
    denom = np.einsum("ij,ij->i", dv, dv)
    tca = -np.einsum("ij,ij->i", dp, dv) / np.maximum(denom, 1e-30)
    tca = np.clip(tca, min(0, t_end), max(0, t_end))
    closest = dp + dv * tca[:, None]
    return np.linalg.norm(closest, axis=1), tca


def one_realization(args):
    """1実現: リサンプル + ±窓の両方向積分。"""
    n, dt, window, seed = args
    rng = np.random.default_rng(seed)
    pos, vel = make_catalog(n, rng)
    # 誤差リサンプル相当 (対角近似のガウス揺動; コストは共分散版でも同オーダー)
    pos = pos + rng.normal(0, 1e-5, pos.shape)
    vel = vel + rng.normal(0, 1 * KMS * 1e-3, vel.shape)
    d1, t1 = propagate_leapfrog(pos, vel, +window, dt)
    d2, t2 = propagate_leapfrog(pos, vel, -window, dt)
    use2 = d2 < d1
    return float(np.min(np.where(use2, d2, d1)))


def bench_single():
    print("== 単一プロセス: 1実現コスト (±10 Myr 両方向積分込み) ==")
    results = {}
    for n in [10_000, 100_000, 1_000_000]:
        for dt in [0.05, 0.01]:
            if n == 1_000_000 and dt == 0.01:
                continue  # 外挿で十分
            t0 = time.perf_counter()
            one_realization((n, dt, 10.0, 42))
            el = time.perf_counter() - t0
            results[(n, dt)] = el
            steps = 2 * int(10.0 / dt)
            print(f"  N={n:>9,}  dt={dt:.2f} Myr ({steps:4d} steps): "
                  f"{el:7.2f} s  ({el / (n * steps) * 1e9:.1f} ns/star/step)")
    print("== 線形伝播 (LMA) 1実現 ==")
    for n in [100_000, 1_000_000]:
        rng = np.random.default_rng(0)
        pos, vel = make_catalog(n, rng)
        t0 = time.perf_counter()
        propagate_linear(pos, vel, 2.0, 0.05)
        el = time.perf_counter() - t0
        print(f"  N={n:>9,}: {el * 1000:7.1f} ms")
    return results


def bench_parallel():
    print("== プロセス並列 (実現方向): N=100,000, dt=0.05, ±10 Myr ==")
    n_real = 12
    for w in [6, 8, 6, 8]:  # FUTURE SIGHT の教訓: 交互に複数回測る
        jobs = [(100_000, 0.05, 10.0, 100 + i) for i in range(n_real)]
        with ProcessPoolExecutor(max_workers=w) as pool:
            list(pool.map(one_realization, jobs[:w]))  # ウォームアップ (計測外)
            t0 = time.perf_counter()
            list(pool.map(one_realization, jobs))
            el = time.perf_counter() - t0
        print(f"  workers={w}: {el:6.1f} s / {n_real} 実現 = "
              f"{el / n_real:.2f} s/実現  ({n_real / el:.2f} 実現/秒)", flush=True)


if __name__ == "__main__":
    np.show_config() if False else None
    bench_single()
    bench_parallel()

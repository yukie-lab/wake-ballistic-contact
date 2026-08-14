"""G3-3 Stage C: 完備性 C(t_ph, d_ph) と補正後接近頻度 (BJ+18 §4 の再現)

構成 (BJ+18 §4.1-4.3):
- mock 観測側: GDR2mock (G<=12.5, 3550<Teff<6900) にノイズ付与
  (σ_ϖ=0.068 mas, σ_μα*=0.059, σ_μδ=0.041 mas/yr, σ_vr=0.8 km/s, 無相関,
  星あたり 100 サンプル) → LMA 近日点
- mock 完全側: F_exp(t,d) = a·d (t 非依存 — 一様場)。BJ の a は非公開のため、
  同一銀河モデル (GDR2mock) の局所 70 pc 完全体積から解析的に再構築:
  a = (2π/V) Σ_i v_i  (v_i: 太陽相対速さ [pc/Myr])
- C = [mock観測側の (t,d) ビン密度] / [a·d̄·Δt·Δd]。ゼロセルは近傍平均。
- n_cor = (1/2000) Σ_サロゲート 1/C、σ = n_cor·√(1/n_enc + f_c²)、f_c=0.1
- 窓 |t|<5 Myr ∧ d<5 pc → /10 Myr → ×(d/5)² スケーリングで 1 pc 値

照合値 (BJ+18): n_enc=463.4 (926,736 サロゲート) / n_cor=4914±542 /
491±54 /Myr @5pc / 19.7±2.2 @1pc / C 平均 0.14 (±5 Myr)・0.09 (±10 Myr) /
C_i<0.01 は 0.4% / 窓±2.5 Myr で 373±44
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
G33 = ROOT / "data" / "g33"

K = 4.74047e-3      # km/s per (mas/yr · pc)
PC_PER_MYR = 1.02271
NOISE = dict(plx=0.068, pmra=0.059, pmdec=0.041, rv=0.8)
N_NOISE = 100
T_EDGES = np.arange(-15.0, 15.0 + 1e-9, 1.0)
D_EDGES = np.arange(0.0, 10.0 + 1e-9, 0.5)
F_C = 0.1


def lma_obs(plx, pmra, pmdec, rv):
    """観測量から LMA 近日点 (t [Myr], d [pc])。plx<=0 は NaN。"""
    ok = plx > 0
    r = np.where(ok, 1000.0 / np.where(ok, plx, 1.0), np.nan)
    mu = np.hypot(pmra, pmdec)
    vt = K * mu * r
    v2 = vt ** 2 + rv ** 2
    d = r * vt / np.sqrt(v2)
    # t_ph^lin = r·(−v_r)/v² [pc/(km/s)] → Myr 換算 ×(1/1.02271)=0.97779
    t = r * (-rv) / v2 * (1.0 / PC_PER_MYR)
    return np.where(ok, t, np.nan), np.where(ok, d, np.nan)


def build_completeness(verbose=True):
    obs = pd.read_parquet(RAW / "gdr2mock_obs_candidates.parquet")
    loc = pd.read_parquet(RAW / "gdr2mock_local70pc.parquet")

    # a の再構築 (局所 70 pc 完全体積)
    r_loc = 1000.0 / loc["parallax"].to_numpy(float)
    vt_loc = K * np.hypot(loc["pmra"], loc["pmdec"]).to_numpy(float) * r_loc
    v_loc = np.hypot(vt_loc, loc["radial_velocity"].to_numpy(float)) * PC_PER_MYR
    V = 4.0 / 3.0 * np.pi * 70.0 ** 3
    a = 2 * np.pi * v_loc.sum() / V   # [pc^-1 Myr^-1]
    if verbose:
        n_dens = len(loc) / V
        print(f"局所完全体積: {len(loc):,} 星 / n={n_dens:.4f} pc⁻³ / "
              f"<v>={v_loc.mean() / PC_PER_MYR:.1f} km/s / a={a:.4f} pc⁻¹Myr⁻¹")

    # mock 観測側 + ノイズ 100 サンプル → LMA
    rng = np.random.default_rng(416)
    n = len(obs)
    plx = obs["parallax"].to_numpy(float)[:, None] + rng.normal(0, NOISE["plx"], (n, N_NOISE))
    pmra = obs["pmra"].to_numpy(float)[:, None] + rng.normal(0, NOISE["pmra"], (n, N_NOISE))
    pmdec = obs["pmdec"].to_numpy(float)[:, None] + rng.normal(0, NOISE["pmdec"], (n, N_NOISE))
    rv = obs["radial_velocity"].to_numpy(float)[:, None] + rng.normal(0, NOISE["rv"], (n, N_NOISE))
    t, d = lma_obs(plx.ravel(), pmra.ravel(), pmdec.ravel(), rv.ravel())
    ok = np.isfinite(t) & np.isfinite(d)
    H, _, _ = np.histogram2d(t[ok], d[ok], bins=[T_EDGES, D_EDGES])
    H /= N_NOISE

    # 期待側 F_exp = a·d̄·Δt·Δd
    d_mid = 0.5 * (D_EDGES[:-1] + D_EDGES[1:])
    dt_bin = np.diff(T_EDGES)[0]
    dd_bin = np.diff(D_EDGES)[0]
    F_exp = a * d_mid[None, :] * dt_bin * dd_bin
    C = H / F_exp

    # ゼロセルの近傍平均置換 (BJ 方式)
    zero = C == 0
    if zero.any():
        from scipy.ndimage import uniform_filter
        smooth = uniform_filter(C, size=3, mode="nearest")
        C = np.where(zero, smooth, C)
    C = np.clip(C, 0.0, None)
    if verbose:
        ti = np.abs(0.5 * (T_EDGES[:-1] + T_EDGES[1:]))
        m5 = C[ti < 5][:, :].mean()
        m10 = C[ti < 10][:, :].mean()
        print(f"C: 最大 {C.max():.2f} / ビン平均 |t|<5: {m5:.3f} (公刊 0.14) / "
              f"|t|<10: {m10:.3f} (公刊 0.09)")
    return C, a


def lookup_C(C, t, d):
    it = np.clip(np.searchsorted(T_EDGES, t) - 1, 0, len(T_EDGES) - 2)
    idx = np.clip(np.searchsorted(D_EDGES, d) - 1, 0, len(D_EDGES) - 2)
    return C[it, idx]


def rate(C, window=5.0, verbose=True):
    z = np.load(G33 / "surrogate_perihelia.npz")
    bright = z["g_mag"] < 12.5
    t_ph = z["t_ph"][bright]
    d_ph = z["d_ph"][bright]
    n_surr = t_ph.shape[1]
    sel = (np.abs(t_ph) < window) & (d_ph < 5.0) & np.isfinite(t_ph)
    n_enc = sel.sum() / n_surr
    Ci = lookup_C(C, t_ph[sel].astype(float), d_ph[sel].astype(float))
    frac_lowC = float((Ci < 0.01).mean()) if Ci.size else 0.0
    Ci = np.maximum(Ci, 1e-4)
    n_cor = (1.0 / Ci).sum() / n_surr
    sigma = n_cor * np.sqrt(1.0 / max(n_enc, 1) + F_C ** 2)
    r5 = n_cor / (2 * window)
    s5 = sigma / (2 * window)
    r1, s1 = r5 * (1 / 5) ** 2, s5 * (1 / 5) ** 2
    if verbose:
        print(f"窓 ±{window} Myr: 星数 {bright.sum()} (公刊 2522) / "
              f"窓内サロゲート {int(sel.sum()):,} / n_enc={n_enc:.1f} / "
              f"C<0.01 割合 {frac_lowC:.1%}")
        print(f"  n_cor = {n_cor:.0f} ± {sigma:.0f}")
        print(f"  rate@5pc = {r5:.0f} ± {s5:.0f} /Myr / rate@1pc = {r1:.1f} ± {s1:.1f} /Myr")
    return r1, s1


def main():
    C, a = build_completeness()
    print("\n== 主計算 (窓 ±5 Myr — BJ+18 §4.3) ==")
    r1, s1 = rate(C, 5.0)
    print("\n== 感度 (窓 ±2.5 Myr — 公刊 373±44 @5pc) ==")
    rate(C, 2.5)
    print("\n== 帯判定 (裁定ログ#4: 厳格 @1pc 15.3-24.1 / 緩和 6-25) ==")
    strict = 15.3 <= r1 <= 24.1
    loose = 6 <= r1 <= 25
    print(f"  厳格: {'PASS' if strict else 'FAIL'} / 緩和: {'PASS' if loose else 'FAIL'}"
          f"  (rate@1pc = {r1:.1f} ± {s1:.1f}, BJ+18 = 19.7 ± 2.2)")
    if not strict:
        print("  → 裁定5 プロトコル: 停止・4点証拠鎖・裁定")
    return 0 if loose else 1


if __name__ == "__main__":
    raise SystemExit(main())

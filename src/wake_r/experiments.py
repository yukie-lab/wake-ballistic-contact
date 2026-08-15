"""Phase R 実験ランナー (チェックポイント §2 の E0-E3)

単位系: R=1(接触半径)、時間は Myr 相当の任意単位。速度 σ は [R/時間]。
装置 (device.contact_process_run) は単位不可知なのでそのまま使う。

生存判定 (有限箱・有限時間の近似):
  survived フラグ (絶滅せず) かつ 末端で伝播が継続 (n_tx が後半も増加) を「生存」。
  箱の規律: σ·t_max ≲ box/3(流出による偽絶滅の予防)。

実行例:
  ~/miniforge3/envs/wake/bin/python src/wake_r/experiments.py pilot
  ~/miniforge3/envs/wake/bin/python src/wake_r/experiments.py E2
"""

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
from concurrent.futures import ProcessPoolExecutor

from wake_r.device import contact_process_run

OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "phase_r"
OUT.mkdir(parents=True, exist_ok=True)

E_VREL = 4.0 / np.sqrt(np.pi)  # E|v_rel| = (4/√π)·σ (等方ガウス、成分σ)


def field(rho, box, sigma, seed):
    """R=1 単位の一様 Poisson 場 + 等方ガウス速度 (成分 σ [R/時間])。"""
    rng = np.random.default_rng(seed)
    n = rng.poisson(rho * box ** 3)
    pos = rng.uniform(-box / 2, box / 2, (n, 3))
    vel = rng.standard_normal((n, 3)) * sigma
    return pos, vel


def one_run(args):
    rho, box, sigma, p, Ts, t_max, seed = args
    pos, vel = field(rho, box, sigma, seed)
    dt = min(0.25, 0.6 / (7 * sigma + 0.2))
    r = contact_process_run(pos, vel, p=p, R_pc=1.0, tau_myr=0.1,
                            Ts_myr=Ts, t_max_myr=t_max, dt_myr=dt, seed=seed)
    n = len(pos)
    half = len(r["t"]) // 2
    grew = bool(r["n_alive"][-1] > 0 and (Ts == np.inf or
                r["n_alive"][-1] >= r["n_alive"][half]))
    return dict(rho=rho, box=box, sigma=sigma, p=p,
                Ts=(None if Ts == np.inf else Ts), t_max=t_max, seed=seed,
                n=n, survived=bool(r["survived"]), grew=grew,
                n_alive_end=int(r["n_alive"][-1]),
                n_tx=int(r["n_transmissions"]), extent=float(r["extent"][-1]),
                marked_frac=float(r["X"][-1]))


def run_grid(name, jobs, workers=6):
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        res = list(pool.map(one_run, jobs))
    (OUT / f"{name}.json").write_text(json.dumps(res, indent=1))
    print(f"[{name}] {len(jobs)} runs / {time.time() - t0:.0f}s -> {name}.json")
    return res


def m_value(rho, sigma, p, Ts):
    deg = 4 * np.pi / 3 * rho
    lam = rho * np.pi * E_VREL * sigma
    return p * (deg + (0 if Ts is None else lam * Ts))


def pilot():
    jobs = [(0.1, 60, 1.0, 0.8, 4.0, 16.0, 1)]
    t0 = time.time()
    r = one_run(jobs[0])
    print(f"pilot: {time.time() - t0:.1f}s / N={r['n']} / survived={r['survived']} "
          f"/ tx={r['n_tx']} / m={m_value(0.1, 1.0, 0.8, 4.0):.2f}")


def E2():
    """静的極限: ボンド RGG パーコレーションとの一致 (C3)。ρR³=1.0, deg=4.19。"""
    jobs = [(1.0, 30, 0.0, p, np.inf, 40.0, s)
            for p in [0.3, 0.45, 0.55, 0.65, 0.75, 0.9]
            for s in range(1, 9)]
    res = run_grid("E2_static", jobs)
    for p in sorted({r["p"] for r in res}):
        rs = [r for r in res if r["p"] == p]
        frac = np.mean([r["marked_frac"] for r in rs])
        big = np.mean([r["marked_frac"] > 0.2 for r in rs])
        print(f"  p={p:.2f}: <X>={frac:.3f}  P(巨大クラスタ)={big:.2f}")


def E3():
    """運動による救済 (C4/層3 デモ): ρR³=1.0, p=0.5 (静的 p_c 以下), σ を上げる。"""
    jobs = [(1.0, 30, s_, 0.5, 3.0, 9.0, seed)
            for s_ in [0.0, 0.1, 0.25, 0.5, 1.0]
            for seed in range(1, 9)]
    res = run_grid("E3_rescue", jobs)
    for s_ in sorted({r["sigma"] for r in res}):
        rs = [r for r in res if r["sigma"] == s_]
        surv = np.mean([r["grew"] for r in rs])
        print(f"  σ={s_:4.2f}: 生存率 {surv:.2f}  m={m_value(1.0, s_, 0.5, 3.0):.2f} "
              f"(<tx>={np.mean([r['n_tx'] for r in rs]):.0f})")


def E1():
    """疎領域の生存境界 (C2/C5): ρR³=0.1 (静的サブクリティカル), p×σ 走査。"""
    jobs = [(0.1, 60, s_, p, 4.0, 16.0, seed)
            for s_ in [0.25, 0.5, 1.0, 1.5]
            for p in [0.2, 0.4, 0.6, 0.8, 1.0]
            for seed in range(1, 9)]
    res = run_grid("E1_sparse", jobs)
    print(f"{'σ':>5} {'p':>5} {'m':>6} {'生存率':>6}")
    for s_ in sorted({r["sigma"] for r in res}):
        for p in sorted({r["p"] for r in res if r["sigma"] == s_}):
            rs = [r for r in res if r["sigma"] == s_ and r["p"] == p]
            surv = np.mean([r["grew"] for r in rs])
            print(f"{s_:5.2f} {p:5.2f} {m_value(0.1, s_, p, 4.0):6.2f} {surv:6.2f}")


def one_run_e4(args):
    sigma, seed, rho, p, Ts, tau = args
    pos, vel = field(rho, 30, sigma, seed)
    dt = min(0.25, 0.6 / (7 * sigma + 0.2))
    r = contact_process_run(pos, vel, p=p, R_pc=1.0, tau_myr=tau,
                            Ts_myr=Ts, t_max_myr=10.0, dt_myr=dt, seed=seed)
    return dict(sigma=sigma, seed=seed, grew=bool(r["n_alive"][-1] > 0),
                n_tx=int(r["n_transmissions"]))


def E4():
    """C-1: 単調性の反例探索。静的閾値近傍 p=0.55、短寿命 T_s=1.5、長遅延 τ=0.5。"""
    sigmas = [0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
    jobs = [(s_, seed, 1.0, 0.55, 1.5, 0.5) for s_ in sigmas for seed in range(1, 17)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e4, jobs))
    (OUT / "E4_monotone.json").write_text(json.dumps(res, indent=1))
    print(f"E4 (C-1): ρR³=1.0, p=0.55, T_s=1.5, τ=0.5 ({time.time()-t0:.0f}s)")
    for s_ in sigmas:
        rs = [r for r in res if r["sigma"] == s_]
        surv = np.mean([r["grew"] for r in rs])
        tx = np.mean([r["n_tx"] for r in rs])
        print(f"  σ={s_:4.2f}: 生存率 {surv:.2f}  (<tx>={tx:7.0f}  m={m_value(1.0, s_, 0.55, 1.5):.2f})")


def E4b():
    """C-1 第2の急所: 静的ぎりぎりパーコレーション ρR³=0.7・p=1・T_s=1.0・τ=1.0。"""
    sigmas = [0.0, 0.03, 0.07, 0.15, 0.3, 0.6, 1.2]
    jobs = [(s_, seed, 0.7, 1.0, 1.0, 1.0) for s_ in sigmas for seed in range(1, 17)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e4, jobs))
    (OUT / "E4b_monotone.json").write_text(json.dumps(res, indent=1))
    print(f"E4b (C-1): ρR³=0.7, p=1.0, T_s=1.0, τ=1.0 ({time.time()-t0:.0f}s)")
    for s_ in sigmas:
        rs = [r for r in res if r["sigma"] == s_]
        print(f"  σ={s_:4.2f}: 生存率 {np.mean([r['grew'] for r in rs]):.2f}  "
              f"(<tx>={np.mean([r['n_tx'] for r in rs]):7.0f}  "
              f"m={m_value(0.7, s_, 1.0, 1.0):.2f})")


def E4c():
    """C-1 決着プローブ: E4b の谷候補 (σ≈0.03) を 64 実現で。"""
    sigmas = [0.0, 0.02, 0.04, 0.08, 0.16]
    jobs = [(s_, seed, 0.7, 1.0, 1.0, 1.0) for s_ in sigmas for seed in range(1, 65)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e4, jobs))
    (OUT / "E4c_dip.json").write_text(json.dumps(res, indent=1))
    print(f"E4c: ρR³=0.7, p=1.0, T_s=1.0, τ=1.0, 64実現 ({time.time()-t0:.0f}s)")
    for s_ in sigmas:
        rs = [r["grew"] for r in res if r["sigma"] == s_]
        m_ = np.mean(rs); se = np.sqrt(m_ * (1 - m_) / len(rs))
        print(f"  σ={s_:4.2f}: 生存率 {m_:.3f} ± {se:.3f}")


def one_run_e5(args):
    kind, seed = args
    rng = np.random.default_rng(seed)
    rho, box, s0 = 0.05, 100.0, 0.5
    n = rng.poisson(rho * box ** 3)
    pos = rng.uniform(-box / 2, box / 2, (n, 3))
    if kind == "gauss":
        vel = rng.standard_normal((n, 3)) * s0
    else:  # 固定速さ (RMS を合わせる: |v| = s0*sqrt(3))
        u = rng.standard_normal((n, 3))
        u /= np.linalg.norm(u, axis=1)[:, None]
        vel = u * (s0 * np.sqrt(3.0))
    r = contact_process_run(pos, vel, p=1.0, R_pc=1.0, tau_myr=0.1,
                            Ts_myr=np.inf, t_max_myr=48.0, dt_myr=0.1, seed=seed)
    return dict(kind=kind, seed=seed, t=[float(x) for x in r["t"][::40]],
                extent=[float(x) for x in r["extent"][::40]])


def E5():
    """C6: 前線成長 — ガウス (非有界) vs 固定速さ (有界)、RMS 一致、T_s=∞。"""
    jobs = [(k, seed) for k in ["gauss", "fixed"] for seed in range(1, 7)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e5, jobs))
    (OUT / "E5_front.json").write_text(json.dumps(res, indent=1))
    print(f"E5 ({time.time()-t0:.0f}s): 前線 extent(t) — 前半/後半の平均成長率比")
    for kind in ["gauss", "fixed"]:
        rs = [r for r in res if r["kind"] == kind]
        ratios = []
        for r in rs:
            t, e = np.array(r["t"]), np.array(r["extent"])
            ok = e < 45.0  # 箱端 (box/2=50) 手前まで
            t, e = t[ok], e[ok]
            if len(t) < 6: continue
            h = len(t) // 2
            v1 = (e[h] - e[1]) / (t[h] - t[1])
            v2 = (e[-1] - e[h]) / (t[-1] - t[h])
            ratios.append(v2 / max(v1, 1e-9))
        print(f"  {kind:6s}: 後半/前半 成長率比 = {np.mean(ratios):.2f} ± "
              f"{np.std(ratios)/np.sqrt(len(ratios)):.2f}  (>1 なら加速 = 超線形の兆候)")


def one_run_e6(seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    rho, box, s0 = 0.05, 100.0, 0.5
    n = rng.poisson(rho * box ** 3)
    pos = rng.uniform(-box / 2, box / 2, (n, 3))
    vel = rng.standard_normal((n, 3)) * s0
    from wake_r.device import contact_process_run
    r = contact_process_run(pos, vel, p=1.0, R_pc=1.0, tau_myr=0.1,
                            Ts_myr=np.inf, t_max_myr=40.0, dt_myr=0.1, seed=seed)
    # 装置はマーク集合を返さないため、extent の加速で代理…ではなく
    # ここでは装置を再現せずに済むよう mark_time を直接得る拡張が必要 → 近似:
    # extent(t)/t の増加列を速さの下界として使う
    t = r["t"]; e = r["extent"]
    idx = [int(len(t)*f) for f in (0.25, 0.5, 0.75, 1.0)]
    return [float(e[i-1] / t[i-1]) for i in idx]


def E6():
    """C6a 機構チェック: extent(t)/t (前線の実効速さ) が単調増大するか (ガウス, T_s=∞)。
    定理の機構: 次第に速い粒子がマークされ前線を運ぶ → R(t)/t は増加列。"""
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e6, range(1, 7)))
    arr = np.array(res)
    (OUT / "E6_speed.json").write_text(json.dumps(res, indent=1))
    labels = ["t=25%", "t=50%", "t=75%", "t=100%"]
    print("E6: 前線実効速さ R(t)/t の推移 (6実現平均, σ=0.5, 最大寄与は裾粒子):")
    for k, lab in enumerate(labels):
        print(f"  {lab}: {arr[:, k].mean():.3f} ± {arr[:, k].std()/np.sqrt(6):.3f}")


def one_run_e7(args):
    sigma, seed = args
    pos, vel = field(0.1, 60, sigma, seed)
    dt = min(0.25, 0.6 / (7 * sigma + 0.2))
    r = contact_process_run(pos, vel, p=1.0, R_pc=1.0, tau_myr=0.1,
                            Ts_myr=4.0, t_max_myr=16.0, dt_myr=dt, seed=seed,
                            hold_myr=0.8)
    return dict(sigma=sigma, seed=seed, grew=bool(r["n_alive"][-1] > 0),
                n_tx=int(r["n_transmissions"]))


def E7():
    """D-1: 滞在時間要求型 (hold=0.8) の σ 依存 — 非単調 (最適速度) の検証。"""
    sigmas = [0.1, 0.2, 0.4, 0.8, 1.6, 3.2]
    jobs = [(s_, seed) for s_ in sigmas for seed in range(1, 17)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e7, jobs))
    (OUT / "E7_dwell.json").write_text(json.dumps(res, indent=1))
    print(f"E7 (D-1 滞在時間型): ρR³=0.1, p=1, T_s=4, hold=0.8 ({time.time()-t0:.0f}s)")
    print("  (参考: σ=0 の静的は deg=0.42 ≪ パーコレーション → 死。進入駆動型なら σ 単調)")
    for s_ in sigmas:
        rs = [r for r in res if r["sigma"] == s_]
        print(f"  σ={s_:4.2f}: 生存率 {np.mean([r['grew'] for r in rs]):.2f}  "
              f"(<tx>={np.mean([r['n_tx'] for r in rs]):7.0f})")


def one_run_e8(args):
    tau, seed = args
    pos, vel = field(0.1, 60, 1.0, seed)
    r = contact_process_run(pos, vel, p=0.8, R_pc=1.0, tau_myr=tau,
                            Ts_myr=2.0, t_max_myr=24.0, dt_myr=0.08, seed=seed)
    return dict(tau=tau, seed=seed, n_ever=r["n_ever"], n_remark=r["n_remark"],
                grew=bool(r["n_alive"][-1] > 0))


def E8():
    """逆向きチャネルの検証 (審査役4の発見): 再マーク率は τ/T_s とともに増えるか。
    予言: 子の到着が親の死後になる τ ≳ T_s で親の再マークが増加。"""
    taus = [0.02, 0.5, 1.0, 2.0, 4.0, 8.0]
    jobs = [(t_, seed) for t_ in taus for seed in range(1, 17)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e8, jobs))
    (OUT / "E8_reverse.json").write_text(json.dumps(res, indent=1))
    print(f"E8 (逆向きチャネル): ρR³=0.1, p=0.8, σ=1, T_s=2 ({time.time()-t0:.0f}s)")
    print(f"{'τ/T_s':>6} {'再マーク率':>8} {'生存率':>6} {'<総事象>':>8}")
    for t_ in taus:
        rs = [r for r in res if r["tau"] == t_]
        tot_re = sum(r["n_remark"] for r in rs)
        tot_ev = sum(r["n_ever"] + r["n_remark"] for r in rs)
        surv = np.mean([r["grew"] for r in rs])
        print(f"{t_/2.0:6.2f} {tot_re/max(tot_ev,1):8.3f} {surv:6.2f} "
              f"{tot_ev/len(rs):8.0f}")


def one_run_e8b(args):
    tau, seed = args
    pos, vel = field(0.05, 40, 0.05, seed)   # 遅い混合: 窓長 ~ R/(2.26·0.05) ≈ 9
    r = contact_process_run(pos, vel, p=1.0, R_pc=1.0, tau_myr=tau,
                            Ts_myr=1.0, t_max_myr=40.0, dt_myr=0.1, seed=seed)
    return dict(tau=tau, seed=seed, n_ever=r["n_ever"], n_remark=r["n_remark"])


def E8b():
    """逆向きチャネル・審査役4の反例レジーム: 遅い相対速度 (長窓) × τ/T_s 走査。
    予言: 親再マーク経路が τ/T_s とともに増え p(1−e^{−2τ/T_s}) で飽和。"""
    taus = [0.1, 0.5, 1.0, 2.0, 4.0]
    jobs = [(t_, seed) for t_ in taus for seed in range(1, 25)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e8b, jobs))
    (OUT / "E8b_reverse.json").write_text(json.dumps(res, indent=1))
    print(f"E8b (反例レジーム): ρR³=0.05, σ=0.05, p=1, T_s=1, 窓長~9 ({time.time()-t0:.0f}s)")
    print(f"{'τ/T_s':>6} {'再マーク率':>8} {'<総事象>':>8} {'飽和予測 p(1-e^-2τ)':>16}")
    import math
    for t_ in taus:
        rs = [r for r in res if r["tau"] == t_]
        tot_re = sum(r["n_remark"] for r in rs)
        tot_ev = sum(r["n_ever"] + r["n_remark"] for r in rs)
        pred = 1.0 * (1 - math.exp(-2 * t_ / 1.0))
        print(f"{t_:6.1f} {tot_re/max(tot_ev,1):8.3f} {tot_ev/len(rs):8.0f} {pred:16.3f}")


def one_run_e8c(seed):
    rho = 0.1 * 3 / (4 * np.pi)   # deg_sup = ρV_R = 0.1
    pos, vel = field(rho, 40, 0.001, seed)  # 準静的 (窓長 ~440 ≫ 多世代×τ)
    r = contact_process_run(pos, vel, p=1.0, R_pc=1.0, tau_myr=10.0,
                            Ts_myr=1.0, t_max_myr=150.0, dt_myr=0.25, seed=seed)
    return r["n_ever"] + r["n_remark"]


def E8c():
    """審査役4の反例の直接判定: p=1, τ=10T_s, deg=0.1, 準静的。
    偽の上界 1/(1-m̄) = 1.111 vs 審査役の下界 ≈ 1.185 を E[N] 実測で判定。"""
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        res = list(pool.map(one_run_e8c, range(1, 10001)))
    arr = np.array(res, dtype=float)
    (OUT / "E8c_counterexample.json").write_text(json.dumps(res))
    mean, se = arr.mean(), arr.std() / np.sqrt(len(arr))
    print(f"E8c ({time.time()-t0:.0f}s, 10000実現): E[総マーク事象数] = {mean:.4f} ± {se:.4f}")
    print(f"  偽の上界 1/(1−m̄) = 1.1111 / 審査役の下界 ≈ 1.185")
    print(f"  判定: {'定理 A-full は数値的にも棄却' if mean - 2*se > 1.1111 else '判定保留'}")


if __name__ == "__main__":
    {"pilot": pilot, "E1": E1, "E2": E2, "E3": E3, "E4": E4, "E4b": E4b,
     "E4c": E4c, "E5": E5, "E6": E6, "E7": E7, "E8": E8, "E8b": E8b,
     "E8c": E8c}[sys.argv[1]]()

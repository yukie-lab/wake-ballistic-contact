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


if __name__ == "__main__":
    {"pilot": pilot, "E1": E1, "E2": E2, "E3": E3}[sys.argv[1]]()

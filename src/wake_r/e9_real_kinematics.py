"""E9 — 実測運動学での m 閾値再測定(裁定ログ#14 付帯2)

E1(等方ガウス・一様 Poisson)で較正した数値閾値 m ≈ 1.0–1.3 は、定理沈黙域の
唯一の判定材料。実測 ν(DR3 100pc 6D — 非等方・ストリーム・裾)で閾値位置が
動くかを再測する。

設計: E1 の σ=1.0 行と**尺度整合**させる — 実測速度(平均減算)を1次元分散が
σ_iso=1.0(R=1 装置単位)になるよう一括スケール。形状(非等方性・裾)だけが
E1 と異なる制御実験。ρ=0.1, box=60, Ts=4, t_max=16, τ=0.1(one_run と同一)。

実行: python3 src/wake_r/e9_real_kinematics.py
出力: data/phase_r/E9_real_kinematics.json + 標準出力の比較表
"""
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from device import contact_process_run, real_catalog_snapshot

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "phase_r"


def real_velocity_pool():
    _, vel = real_catalog_snapshot()          # pc/Myr
    vel = vel - vel.mean(axis=0)              # 共通ドリフト除去(ガリレイ不変)
    sig1d = vel.std(axis=0).mean()
    return vel / sig1d                        # 1次元分散 1.0 に正規化


def one_run_e9(args):
    p, seed, vel_pool_path = args
    rho, box, Ts, t_max = 0.1, 60, 4.0, 16.0
    rng = np.random.default_rng(seed)
    n = rng.poisson(rho * box ** 3)
    pos = rng.uniform(-box / 2, box / 2, (n, 3))
    pool = np.load(vel_pool_path)["v"]
    vel = pool[rng.integers(0, len(pool), n)]
    dt = min(0.25, 0.6 / (7 * 1.0 + 0.2))
    r = contact_process_run(pos, vel, p=p, R_pc=1.0, tau_myr=0.1,
                            Ts_myr=Ts, t_max_myr=t_max, dt_myr=dt, seed=seed)
    half = len(r["t"]) // 2
    grew = bool(r["n_alive"][-1] > 0 and r["n_alive"][-1] >= r["n_alive"][half])
    # m = p(deg + λTs): λ は標本の平均相対速さから
    sub = vel[rng.integers(0, n, 4000)]
    e_rel = float(np.linalg.norm(sub[:2000] - sub[2000:], axis=1).mean())
    m = p * (4 * np.pi / 3 * rho + rho * np.pi * e_rel * Ts)
    return dict(p=p, seed=seed, grew=grew, m=round(m, 3),
                n_tx=int(r["n_transmissions"]))


def main():
    pool = real_velocity_pool()
    tmp = OUT / "e9_velpool.npz"
    np.savez_compressed(tmp, v=pool)
    print(f"実測速度プール: {len(pool):,} 星(正規化済み)")
    jobs = [(p, seed, str(tmp)) for p in (0.2, 0.3, 0.4, 0.6, 0.8, 1.0)
            for seed in range(1, 17)]
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one_run_e9, jobs))
    (OUT / "E9_real_kinematics.json").write_text(json.dumps(res, indent=1))
    print(f"{'p':>5} {'m':>6} {'生存率(実測ν)':>12}")
    for p in sorted({r["p"] for r in res}):
        rs = [r for r in res if r["p"] == p]
        surv = np.mean([r["grew"] for r in rs])
        print(f"{p:5.2f} {np.mean([r['m'] for r in rs]):6.2f} {surv:12.2f}")
    print("比較: E1(等方ガウス σ=1.0)の同スケール走査では閾値 m ≈ 1.0–1.3")


if __name__ == "__main__":
    main()

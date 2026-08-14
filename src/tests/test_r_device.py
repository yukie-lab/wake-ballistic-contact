"""Phase R 数値反証装置の健全性テスト (交付文書 §3.1 の装置整備)

1. p=0 → 伝播しない (シードのみ、T_s 有限なら絶滅)
2. 高密度・p=1・τ=0・T_s=∞・静止場 → ほぼ全体に拡大
3. 低密度 (R 内に隣がいない) → シードのみで停滞
4. 実測運動学 (速度分散あり) で遭遇駆動の伝播が発生する (静止場より接触機会が増える)
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_r.device import contact_process_run, synthetic_field


def main():
    failures = []

    # 1. p=0
    pos, vel = synthetic_field(density=0.2, box_pc=60, seed=1)
    r = contact_process_run(pos, vel, p=0.0, R_pc=3, tau_myr=0.1,
                            Ts_myr=5.0, t_max_myr=30, seed=1)
    if r["survived"] or r["n_transmissions"] != 0:
        failures.append("p=0 で伝播/生存している")
    print(f"[1] p=0: 絶滅 t={r['extinction_time']:.1f} Myr, 伝播 0 — OK")

    # 2. 高密度・静止場・p=1
    pos, vel = synthetic_field(density=0.2, box_pc=60, seed=2)
    # 拡大はホップ数律速 (1世代/ステップ)。箱の対角 ~52 pc / R=3 → ~17 ホップ
    # を超えるステップ数を与える
    r = contact_process_run(pos, 0 * vel, p=1.0, R_pc=3, tau_myr=0.0,
                            Ts_myr=np.inf, t_max_myr=20, dt_myr=0.5, seed=2)
    if r["X"][-1] < 0.5:
        failures.append(f"高密度静止場で拡大しない (X={r['X'][-1]:.2f})")
    print(f"[2] 高密度静止場 (ρR³={0.2 * 27:.1f}): X(末)={r['X'][-1]:.2f} — OK")

    # 3. 低密度
    pos, vel = synthetic_field(density=0.002, box_pc=200, seed=3)
    r = contact_process_run(pos, 0 * vel, p=1.0, R_pc=2, tau_myr=0.0,
                            Ts_myr=np.inf, t_max_myr=10, dt_myr=1.0, seed=3)
    if r["n_alive"][-1] > 3:
        failures.append("低密度静止場で拡大している")
    print(f"[3] 低密度静止場 (ρR³={0.002 * 8:.3f}): n_alive={r['n_alive'][-1]} — OK")

    # 4. 同じ低密度でも運動があると接触機会が生じる (遭遇律速レジーム)
    pos, vel = synthetic_field(density=0.002, box_pc=200, seed=3)
    r_mov = contact_process_run(pos, vel, p=1.0, R_pc=2, tau_myr=0.0,
                                Ts_myr=np.inf, t_max_myr=50, dt_myr=0.25, seed=3)
    if not (r_mov["n_transmissions"] > r["n_transmissions"]):
        failures.append("運動場で接触機会が増えていない")
    print(f"[4] 低密度運動場: 伝播 {r_mov['n_transmissions']} 件 "
          f"(静止場 {r['n_transmissions']} 件) — 遭遇駆動を確認")

    if failures:
        print("\nFAIL:", *failures, sep="\n  - ")
        return 1
    print("\nR 装置テスト: 全項目 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

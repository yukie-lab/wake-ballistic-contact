"""G2 スモークテスト: 数値経路 vs エピサイクル解析経路の toy 一致 (±2 Myr)

Phase 1 出口条件「G2 予備確認 (100 星規模)」の先行版。
- 数値: wake_engine (MWPotential2014, 銀河中心系リープフロッグ)
- 解析: wake_epicyclic (太陽相対の線形伝播 — 線形方程式なので2解の差も解であり、
  相対運動を直接伝播してよい)
- 両者は独立実装 (コード共有なし)。Oort 定数のみ数値側ポテンシャルから導出した
  値を解析側に与える (整合条件 — メモ2 §3。これはデータの受け渡しでありコード共有ではない)

合格基準 (暫定・スモーク用、実測残差に基づく設計):
- 接近候補 (d_ph < 20 pc): Δd_ph < 0.005 pc かつ Δt_ph < 0.01 Myr
  (G2 の判定対象はここ。実測: 10 pc 以内で max 0.74 mpc)
- 全ペア: Δd_ph < 0.05 pc (窓端で ~150 pc 離れる遠距離ペアは線形化2次項が
  効き ~0.013 pc の残差が出る。これは実装バグではなく近似の物理的限界 —
  メモ2 §3 の Makarov+04 の適用限界の現れ)
公式の G2 予備確認の基準は Phase 1 冒頭裁定後に固定する。
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_engine import MWPotential2014, closest_approach, sun_state, KMS
from wake_epicyclic import EpicyclicFrame


def main():
    rng = np.random.default_rng(11)
    n = 100
    # 太陽相対の toy 星団 (pc / km/s)。接近が起こるよう位置と速度を相関させる
    rel_pos_pc = rng.normal(0, 30, (n, 3))
    rel_vel_kms = -rel_pos_pc * rng.uniform(0.3, 0.7, (n, 1)) + rng.normal(0, 15, (n, 3))

    mw = MWPotential2014()
    sp, sv = sun_state(mw)
    pos_gal = sp + rel_pos_pc * 1e-3          # kpc
    vel_gal = sv + rel_vel_kms * KMS

    enc_num = closest_approach(mw, pos_gal, vel_gal, window=2.0, dt=0.002)

    A, B, _ = mw.oort_constants(mw.R0)
    # 鉛直振動数もポテンシャルから数値導出して整合させる (スモークは実装バグの
    # 分離が目的。本番 G2 では解析側の定数は独立に裁定した値を使う)
    h = 1e-4
    az = mw.accel(np.array([[mw.R0, 0, +h], [mw.R0, 0, -h]]))[:, 2]
    nu = float(np.sqrt(-(az[0] - az[1]) / (2 * h)))         # Myr^-1
    frame = EpicyclicFrame(A=A, B=B, nu=nu)
    rel_vel_rot = frame.inertial_to_rotating(rel_pos_pc, rel_vel_kms)
    t_epi, d_epi, edge_epi = frame.closest_approach(rel_pos_pc, rel_vel_rot,
                                                    window=2.0, n_samples=4001)

    ok = ~(enc_num.at_edge | edge_epi)        # 窓端イベントは比較対象外
    dd = np.abs(enc_num.d_min[ok] * 1e3 - d_epi[ok])       # pc
    dt = np.abs(enc_num.t_min[ok] - t_epi[ok])              # Myr
    print(f"比較対象: {ok.sum()}/{n} 星 (窓端 {n - ok.sum()} 星を除外)")
    print(f"Δd_ph: max {dd.max():.5f} pc / median {np.median(dd):.5f} pc")
    print(f"Δt_ph: max {dt.max():.5f} Myr / median {np.median(dt):.5f} Myr")
    cand = enc_num.d_min[ok] * 1e3 < 20.0
    print(f"接近候補 (d<20 pc) {cand.sum()} 星: Δd max {dd[cand].max():.5f} pc, "
          f"Δt max {dt[cand].max():.5f} Myr")

    failures = []
    if dd[cand].max() > 0.005:
        failures.append(f"候補 Δd_ph 超過: {dd[cand].max():.4f} pc > 0.005")
    if dt[cand].max() > 0.01:
        failures.append(f"候補 Δt_ph 超過: {dt[cand].max():.4f} Myr > 0.01")
    if dd.max() > 0.05:
        failures.append(f"全ペア Δd_ph 超過: {dd.max():.4f} pc > 0.05")
    if failures:
        print("FAIL:", *failures, sep="\n  - ")
        return 1
    print("\nG2 スモーク: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

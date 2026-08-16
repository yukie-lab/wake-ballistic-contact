"""Phase 4 G2 対経路 — 最良乗換の直接軌道最適化(PHASES 1.2 (4))

グラフ側の線形巡航 Δv 推定を、実ポテンシャル中の二点境界値問題
(シューティング法: 数値伝播で x_i(t_i) → x_j(t_j) を撃ち当てる)と照合する。
グラフ探索とはコード経路が独立(こちらは wake_engine の数値積分のみ使用)。

併せて経路存在統計のアンサンブル(誤差 MC 標本)+ G1 収束(標本数半減安定性)。

実行: python3 src/wake_p4/g2_path_check.py → docs/phase4/02-g2-path.md
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_p4.flyby_network import nominal_perihelia, min_transfer, PC_PER_MYR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase4" / "02-g2-path.md"


def shoot_leg(pot, x_dep_pc, t_dep, x_arr_pc, t_arr, sun):
    """太陽相対位置 x_dep(t_dep) から x_arr(t_arr) へのシューティング。
    巡航速度 u [km/s] を返す(数値伝播・ニュートン修正)。"""
    from wake_engine.coords import helio_galactic_to_engine
    from wake_engine import KMS
    dt_myr = t_arr - t_dep
    u = (x_arr_pc - x_dep_pc) / dt_myr / PC_PER_MYR      # 線形初期推定 [km/s]
    sp, sv = sun

    def endpoint(u_batch):
        """複数の巡航速度候補を一括伝播し終端の太陽相対位置 [pc] を返す"""
        nb = len(u_batch)
        P, V = helio_galactic_to_engine(pot, np.tile(x_dep_pc, (nb, 1)),
                                        np.asarray(u_batch))
        X = np.vstack([sp[None], P])
        Vf = np.vstack([sv[None], V])
        h = np.sign(dt_myr) * 0.002
        a = pot.accel(X)
        n = int(round(abs(dt_myr) / 0.002))
        for _k in range(n):
            Vf += 0.5 * h * a
            X += h * Vf
            a = pot.accel(X)
            Vf += 0.5 * h * a
        return (X[1:] - X[0]) * 1e3

    miss = np.full(3, np.inf)
    for _ in range(10):
        eps = 0.5   # km/s の差分刻み
        batch = [u, u + [eps, 0, 0], u + [0, eps, 0], u + [0, 0, eps]]
        ends = endpoint(batch)
        miss = x_arr_pc - ends[0]
        if np.linalg.norm(miss) < 1e-4:      # 0.1 mpc
            break
        J = np.stack([(ends[1 + k] - ends[0]) / eps for k in range(3)], axis=1)
        try:
            du = np.linalg.solve(J, miss)
        except np.linalg.LinAlgError:
            du = miss / dt_myr / PC_PER_MYR
        # 過大修正の抑制(位相回転域の安定化)
        nrm = np.linalg.norm(du)
        if nrm > 20.0:
            du *= 20.0 / nrm
        u = u + du
    return u, float(np.linalg.norm(miss))


def main():
    from wake_engine import MWPotential2014, sun_state
    idxs, tmed, x_peri, vel = nominal_perihelia()
    d_close = np.linalg.norm(x_peri, axis=1)
    lines = ["# Phase 4 G2 対経路+経路統計(裁定ログ#14 裁定2)", "",
             "> グラフ(線形巡航)vs 直接軌道最適化(数値シューティング)。実行: "
             "`python3 src/wake_p4/g2_path_check.py`", "",
             "## G2: 最良乗換の直接最適化照合", "",
             "| d_visit | ペア | 線形 Δv | 数値 Δv | 差 | miss |",
             "|---|---|---|---|---|---|"]
    pot = MWPotential2014()
    sun = sun_state(pot)
    worst = 0.0
    for d_visit in (0.1, 0.5, 1.0):
        best, pair = min_transfer(tmed, x_peri, vel, d_close, d_visit)
        if pair is None:
            continue
        i, j = pair
        u_lin = (x_peri[j] - x_peri[i]) / (tmed[j] - tmed[i]) / PC_PER_MYR
        dv_lin = float(np.linalg.norm(u_lin - vel[i]))
        u_num, miss = shoot_leg(pot, x_peri[i], tmed[i], x_peri[j], tmed[j], sun)
        dv_num = float(np.linalg.norm(u_num - vel[i]))
        diff = abs(dv_num - dv_lin)
        worst = max(worst, diff)
        lines.append(f"| {d_visit} | {int(idxs[i])}→{int(idxs[j])} | "
                     f"{dv_lin:.3f} | {dv_num:.3f} | {diff:.3f} | {miss:.5f} |")
        print(f"d_visit={d_visit}: 線形 {dv_lin:.3f} vs 数値 {dv_num:.3f} km/s "
              f"(差 {diff:.3f}, miss {miss:.5f} pc)")
    verdict = "PASS(差 < 0.5 km/s — 潮汐項は乗換 Δv の従属変数)" if worst < 0.5 \
        else f"要監査(最大差 {worst:.2f} km/s)"
    lines += ["", f"**G2 判定: {verdict}**", ""]

    # 経路存在統計(誤差アンサンブル — 時刻・速度の摂動、位置は線形補正)
    cat = np.load(P2 / "catalog_ingested.npz")
    rng = np.random.default_rng(7)
    sig_t = 0.1 * np.maximum(np.abs(tmed), 0.5)     # 保守的な時刻散布(CI 代理)
    sig_v = np.minimum(cat["rv_error"][idxs], 5.0)  # 速度散布の代表(≤5 km/s)
    dvs = {0.1: [], 0.5: [], 1.0: []}
    N_ENS = 32
    for k in range(N_ENS):
        t_k = tmed + rng.normal(0, sig_t)
        v_k = vel + rng.normal(0, sig_v[:, None] / np.sqrt(3), vel.shape)
        x_k = x_peri + v_k * PC_PER_MYR * (t_k - tmed)[:, None] * 0  # 位置は名目
        d_k = np.linalg.norm(x_k, axis=1)
        for dv_ in dvs:
            b, _ = min_transfer(t_k, x_k, v_k, d_k, dv_)
            dvs[dv_].append(b)
    lines += ["## 経路存在統計(N=32 アンサンブル、時刻・速度摂動)", "",
              "| d_visit | 存在確率 | 最小Δv 中央値 [CI68] | 半減安定性(G1) |",
              "|---|---|---|---|"]
    for dv_, arr in dvs.items():
        arr = np.array(arr)
        fin = np.isfinite(arr)
        p_exist = fin.mean()
        med = np.median(arr[fin]) if fin.any() else np.nan
        lo, hi = (np.quantile(arr[fin], [0.16, 0.84]) if fin.any()
                  else (np.nan, np.nan))
        m1, m2 = np.median(arr[fin][:16]), np.median(arr[fin])
        stab = abs(m1 - m2) / max(m2, 1e-9)
        lines.append(f"| {dv_} | {p_exist:.0%} | {med:.2f} [{lo:.2f},{hi:.2f}] | "
                     f"{stab:.1%} |")
        print(f"統計 d_visit={dv_}: P(存在)={p_exist:.0%} medΔv={med:.2f}")
    lines += ["", "位置は名目固定・時刻/速度のみ摂動する軽量アンサンブル"
              "(全数値再抽出は v1.1)。半減安定性 < 10% を G1 収束の目安とする。", ""]
    OUT.write_text("\n".join(lines))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()

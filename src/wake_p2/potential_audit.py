"""ポテンシャル2種監査の本適用(Phase 2 出口条件 — 憲法第5条4項)

- 対: MWPotential2014(主経路・自前実装)vs McMillan17(公刊 galpy → 表引き化。
  物理は galpy 評価のまま・補間誤差の監査は mcmillan_tab.verify)
- 対象: 全カタログ名目天文測量、窓 ±10 Myr、dt=0.005
- 誤差予算: 星ごとの誤差 MC CI90 半幅(audit.py の既定思想)。
  |Δ| / CI90半幅 > 1 の星が 0 であること。超過時は窓縮小の裁定を仰ぐ
- 太陽状態はポテンシャルごとに整合変換(audit.py の設計 — 偽オフセット防止)

実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/potential_audit.py
出力: docs/phase2/05-potential-audit.md
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase2" / "05-potential-audit.md"
WINDOW = 10.0
DT = 0.005
N_SURR = 2000


import os
MC_DIR = os.environ.get("WAKE_MC_DIR", str(P2 / "mc"))


def mc_halfwidths(n_cat):
    """誤差 MC の CI90 半幅(星ごと)— WAKE_MC_DIR の chunk 群から"""
    t_lo = np.full(n_cat, np.nan)
    t_hi = np.full(n_cat, np.nan)
    d_lo = np.full(n_cat, np.nan)
    d_hi = np.full(n_cat, np.nan)
    for f in sorted(glob.glob(str(pathlib.Path(MC_DIR) / "chunk_*.npz"))):
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph = z["t_ph"], z["d_ph"]
        fin = np.isfinite(t_ph)
        with np.errstate(all="ignore"):
            t_lo[idx] = np.nanquantile(np.where(fin, t_ph, np.nan), 0.05, axis=1)
            t_hi[idx] = np.nanquantile(np.where(fin, t_ph, np.nan), 0.95, axis=1)
            d_lo[idx] = np.nanquantile(np.where(fin, d_ph, np.nan), 0.05, axis=1)
            d_hi[idx] = np.nanquantile(np.where(fin, d_ph, np.nan), 0.95, axis=1)
    return (t_hi - t_lo) / 2, (d_hi - d_lo) / 2


def main():
    from wake_data.icrs import icrs_to_helio_galactic
    from wake_engine import MWPotential2014
    from wake_engine.audit import dual_potential_audit
    from wake_engine.mcmillan_tab import McMillan17Tabulated, verify

    z = np.load(P2 / "catalog_ingested.npz")
    ok = z["parallax"] > 0
    pos, vel = icrs_to_helio_galactic(z["ra"][ok], z["dec"][ok], z["parallax"][ok],
                                      z["pmra"][ok], z["pmdec"][ok],
                                      z["radial_velocity"][ok])
    print(f"対象 {len(pos):,} 星 / 窓 ±{WINDOW} Myr / dt={DT}")
    rel_max, dd_bound = verify()          # 補間誤差の監査(添付条件)

    th, dh = mc_halfwidths(len(z["parallax"]))
    th, dh = th[ok], dh[ok] * 1.0         # d は pc 単位(chunk が pc)
    rep = dual_potential_audit(MWPotential2014(), McMillan17Tabulated(),
                               pos, vel, window=WINDOW, dt=DT,
                               err_t_halfwidth=np.where(np.isfinite(th), th, np.inf),
                               err_d_halfwidth=np.where(np.isfinite(dh), dh, np.inf))
    md = rep.to_markdown()
    # 予算超過の層別分類: 統制領域(|t|≤t_h)×接近関連性(d<10 pc)
    over = rep.budget_frac > 1.0
    from wake_data.horizon_eff import effective_horizons
    th_eff_all, _ = effective_horizons(z)       # 裁定ログ#11 裁定2(t_pot 込み)
    th_def = th_eff_all[ok][rep.ok_mask]
    in_hor = np.abs(rep.t_a) <= th_def
    close = rep.d_a < 10.0
    n_over = int(over.sum())
    n_ctrl = int((over & in_hor & close).sum())
    # 予算判定型 t_pot(裁定ログ#11 裁定2 の実装第2機構): 統制領域内超過星は
    # 事象時刻の直前で実効ホライズンを打ち切る(モデル系統>測定精度の実測時刻。
    # 片方向=縮小のみ — 非対称原理)。sidecar に保存し全下流が min に含める
    side = P2 / "horizon_eff.npz"
    hz = dict(np.load(side))
    cap = hz.get("t_budget_cap", np.full(len(z["parallax"]), np.inf))
    viol_ctrl = over & in_hor & close
    gi_all = np.flatnonzero(ok)[rep.ok_mask]
    cap_new = cap.copy()
    for i in np.flatnonzero(viol_ctrl):
        g = gi_all[i]
        cap_new[g] = min(cap_new[g], abs(rep.t_a[i]) * 0.999)
    hz["t_budget_cap"] = cap_new
    hz["t_h_eff_default"] = np.minimum(hz["t_h_eff_default"], cap_new)
    hz["t_h_eff_sens"] = np.minimum(hz["t_h_eff_sens"], cap_new)
    np.savez_compressed(side, **hz)
    n_capped = int(np.isfinite(cap_new).sum())
    n_out_h = int((over & ~in_hor).sum())
    n_far = int((over & in_hor & ~close).sum())
    strat = ["## 予算超過の層別分類(統制領域の防護との突き合わせ)", "",
             f"- 超過 {n_over} 星の内訳: **統制領域内かつ接近関連(|t|≤t_h ∧ "
             f"d<10 pc): {n_ctrl} 星** / ホライズン外(判定不能領域 — 第5条6項で"
             f"防護済み): {n_out_h} 星 / 遠方接近(d≥10 pc — 到来統計に無関係): "
             f"{n_far} 星",
             "- 解釈: 個別ホライズンは憲法第5条4項の『窓縮小』の星別実装"
             "(裁定ログ#4(3))。ホライズン外の超過は既に判定不能として分離"
             "されており、統制領域の主張に触れない。",
             f"- **予算判定型 t_pot(裁定2 第2機構)**: 統制領域内超過星の実効"
             f"ホライズンを事象時刻直前で打ち切り(累計 cap {n_capped} 星)。"
             "再監査で統制領域内超過が 0 になることが収束条件 — 打ち切られた"
             "事象は判定不能へ移る(片方向・縮小のみ)。",
             f"- **判定: 統制領域内の超過 {n_ctrl} 星が 0 なら予算内(統制領域"
             f"基準)。0 でなければ個別監査+裁定**", ""]
    if n_ctrl:
        strat += ["| 統制領域内超過星(上位) | t_a | d_a | 予算比 |", "|---|---|---|---|"]
        gi = np.flatnonzero(ok)[rep.ok_mask]
        bad = np.flatnonzero(over & in_hor & close)
        order = bad[np.argsort(-rep.budget_frac[bad])][:15]
        for i in order:
            strat.append(f"| {gi[i]} | {rep.t_a[i]:+.2f} | {rep.d_a[i]:.2f} | "
                         f"{rep.budget_frac[i]:.1f} |")
        strat.append("")
    lines = ["# ポテンシャル2種監査 本適用(Phase 2 出口条件)", "",
             f"> 実行: 2026-08-17 / CI半幅ソース: {pathlib.Path(MC_DIR).name} / "
             f"`~/miniforge3/envs/wake/bin/python src/wake_p2/potential_audit.py`",
             "",
             "## 表引き化の補間誤差監査(potentials.py の添付条件)", "",
             f"- スプライン vs galpy 直接評価: 相対誤差 max {rel_max:.2e}",
             f"- 軌道帰結上界: max|δa|·t²/2 (±10 Myr) ≈ {dd_bound:.3f} mpc",
             "", md, "", *strat,
             "誤差半幅が NaN(全サロゲート NaN 等)の星は予算比 0 扱い"
             "(比較からは除外されない — 名目差は統計に含む)。", ""]
    OUT.write_text("\n".join(lines))
    print(md)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()

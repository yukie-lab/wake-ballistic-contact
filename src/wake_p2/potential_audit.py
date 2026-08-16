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


def mc_halfwidths(n_cat):
    """誤差 MC の CI90 半幅(星ごと)— 監査時点の chunk 群から"""
    t_lo = np.full(n_cat, np.nan)
    t_hi = np.full(n_cat, np.nan)
    d_lo = np.full(n_cat, np.nan)
    d_hi = np.full(n_cat, np.nan)
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
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
    lines = ["# ポテンシャル2種監査 本適用(Phase 2 出口条件)", "",
             f"> 実行: 2026-08-16 / "
             f"`~/miniforge3/envs/wake/bin/python src/wake_p2/potential_audit.py`",
             "",
             "## 表引き化の補間誤差監査(potentials.py の添付条件)", "",
             f"- スプライン vs galpy 直接評価: 相対誤差 max {rel_max:.2e}",
             f"- 軌道帰結上界: max|δa|·t²/2 (±10 Myr) ≈ {dd_bound:.3f} mpc",
             "", md, "",
             "誤差半幅が NaN(全サロゲート NaN 等)の星は予算比 0 扱い"
             "(比較からは除外されない — 名目差は統計に含む)。", ""]
    OUT.write_text("\n".join(lines))
    print(md)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()

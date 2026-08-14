"""Phase 2 取込: DR3 候補カタログ → 検疫・S値・ホライズン付き作業カタログ

裁定準拠:
- 視差ゼロ点: v1 は全球平均 +0.017 mas (Lindegren+21 の中央値級)。Z5 完全模型への
  精密化は Phase 2 中の改良項目 (LMA 25 pc 余裕が吸収)
- 検疫 (裁定ログ#4): bit1 RUWE / bit2 PM S/N / bit3 RV外れ値+ホワイトリスト。
  bit0 (WD) は外部クロスマッチ未了のため未適用 — 会計に明記
- S 値: gaiaunlimited DR3RVSSelectionFunction (裁定ログ#6 要件(iii))。
  NaN (疎ビン) は判定不能会計へ
- σ(S): dr3-rvs-nk.h5 の (n, k) から Beta 分散を直接計算 (s_floor 第二段材料 — 要件(ii))

実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/ingest.py
出力: data/p2/catalog_ingested.npz + 会計レポート (stdout + meta)
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from wake_data.catalog import StarCatalog
from wake_data.quarantine import apply_quarantine
from wake_data.horizon import horizons, LEGEND_NOTE
from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
P2 = ROOT / "data" / "p2"
PLX_ZP_DR3 = 0.017  # mas (加算)。v1 近似 — Z5 模型へ精密化予定


def build_catalog():
    df = pd.read_parquet(RAW / "dr3_candidates_lma25.parquet")
    n = len(df)
    g = lambda c: df[c].to_numpy(float)
    teff = g("rv_template_teff")
    data = {
        "source_id": df["source_id"].to_numpy(np.int64),
        "ra": g("ra"), "dec": g("dec"),
        "parallax": g("parallax") + PLX_ZP_DR3,
        "pmra": g("pmra"), "pmdec": g("pmdec"),
        "radial_velocity": g("radial_velocity"),
        "ra_error": g("ra_error"), "dec_error": g("dec_error"),
        "parallax_error": g("parallax_error"),
        "pmra_error": g("pmra_error"), "pmdec_error": g("pmdec_error"),
        "rv_error": g("radial_velocity_error"),
        "corr_ra_dec": g("ra_dec_corr"), "corr_ra_parallax": g("ra_parallax_corr"),
        "corr_ra_pmra": g("ra_pmra_corr"), "corr_ra_pmdec": g("ra_pmdec_corr"),
        "corr_dec_parallax": g("dec_parallax_corr"),
        "corr_dec_pmra": g("dec_pmra_corr"), "corr_dec_pmdec": g("dec_pmdec_corr"),
        "corr_parallax_pmra": g("parallax_pmra_corr"),
        "corr_parallax_pmdec": g("parallax_pmdec_corr"),
        "corr_pmra_pmdec": g("pmra_pmdec_corr"),
        "phot_g_mean_mag": g("phot_g_mean_mag"),
        "bp_rp": g("bp_rp"),
        "ruwe": g("ruwe"),
        "rv_provenance": np.zeros(n, dtype=np.int8),
        "rvs_teff_flag": np.where(np.isnan(teff), -1,
                                  ((teff >= 3100) & (teff <= 14500))).astype(np.int8),
        "quarantine_flags": np.zeros(n, dtype=np.int16),
        "s_completeness": np.full(n, np.nan),
    }
    cat = StarCatalog(data=data, release="GaiaDR3-cand-lma25", ref_epoch=2016.0,
                      meta={"plx_zp_mas": PLX_ZP_DR3, "n_raw": n})
    return cat, df


def attach_selection(cat, df):
    """gaiaunlimited S と σ(S) を付与。"""
    from gaiaunlimited.selectionfunctions import DR3RVSSelectionFunction
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    sf = DR3RVSSelectionFunction()
    coords = SkyCoord(ra=cat.data["ra"] * u.deg, dec=cat.data["dec"] * u.deg)
    grp = cat.data["phot_g_mean_mag"] - df["phot_rp_mean_mag"].to_numpy(float)
    S = np.asarray(sf.query(coords, g=cat.data["phot_g_mean_mag"], c=grp),
                   dtype=float)
    cat.data["s_completeness"] = S
    # σ(S): 同じ (ipix, g, c) ビンの n, k から Beta 分散
    ds = sf.ds  # xarray Dataset (n, k)
    import healpy as hp
    order = int(np.log2(np.sqrt(ds["n"].shape[0] // 12))) if False else 5
    ipix = hp.ang2pix(2 ** order, cat.data["ra"], cat.data["dec"],
                      lonlat=True, nest=True)
    g_bins = ds["g"].values
    c_bins = ds["c"].values
    gi = np.clip(np.searchsorted(g_bins, cat.data["phot_g_mean_mag"]) - 1,
                 0, len(g_bins) - 1)
    ci = np.clip(np.searchsorted(c_bins, grp) - 1, 0, len(c_bins) - 1)
    n_arr = ds["n"].values[ipix, gi, ci]
    k_arr = ds["k"].values[ipix, gi, ci]
    var = ((k_arr + 1) * (n_arr - k_arr + 1)
           / ((n_arr + 2) ** 2 * (n_arr + 3)))
    sigma_S = np.sqrt(var)
    return S, sigma_S, n_arr, k_arr


def main():
    P2.mkdir(parents=True, exist_ok=True)
    cat, df = build_catalog()
    qcat, rep = apply_quarantine(cat)  # bit0 (WD) は未適用 (外部クロスマッチ未了)
    print("検疫会計:", rep.as_metadata()["quarantine"]["counts"],
          f"/ ホワイトリスト {rep.n_whitelisted} / 個別判定不能に合流 {rep.n_event_ineligible}")

    try:
        S, sigma_S, n_arr, k_arr = attach_selection(qcat, df)
        ok = np.isfinite(S)
        print(f"S 値: 有限 {ok.sum():,}/{len(S):,} (NaN 疎ビン {np.sum(~ok):,} → 判定不能会計)")
        print(f"S 分布 (有限のみ): 中央値 {np.nanmedian(S):.3f} / "
              f"10% {np.nanpercentile(S, 10):.3f} / 90% {np.nanpercentile(S, 90):.3f}")
        print(f"σ(S) 中央値 {np.nanmedian(sigma_S):.4f}")
        # s_floor 第二段材料: カバレッジ曲線 (実 S 分布)
        print("\ns_floor カバレッジ曲線 (S≥floor の星割合 — 第二段裁定材料):")
        for fl in [0.01, 0.02, 0.05, 0.1, 0.2]:
            cov = float(np.mean(S[ok] >= fl))
            med_sig = float(np.nanmedian(sigma_S[ok][S[ok] >= fl] / S[ok][S[ok] >= fl]))
            print(f"  floor={fl:5.2f}: カバレッジ {cov:.3f} / 相対σ(S) 中央値 {med_sig:.3f}")
    except Exception as e:
        print(f"警告: S 付与に失敗 ({e}) — S=NaN のまま保存 (本計算は率補正前段まで可)")
        S = qcat.data["s_completeness"]
        sigma_S = np.full(len(S), np.nan)

    hz = horizons(qcat.data, R_pc=5.0)
    np.savez_compressed(
        P2 / "catalog_ingested.npz",
        **{k: v for k, v in qcat.data.items()},
        sigma_S=sigma_S,
        t_h_default=hz["t_h_default_myr"], t_h_sens=hz["t_h_sensitivity_myr"],
    )
    (P2 / "ingest_meta.txt").write_text(
        f"{qcat.meta}\nhorizon_legend: {LEGEND_NOTE}\ns_floor: {S_FLOOR}\n"
        f"bit0_wd: 未適用 (外部クロスマッチ未了 — 判定不能会計に明記)\n")
    print(f"\n保存: {P2 / 'catalog_ingested.npz'} ({len(qcat)} 星)")


if __name__ == "__main__":
    main()

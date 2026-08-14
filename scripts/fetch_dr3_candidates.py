"""Phase 2 本計算の DR3 候補カタログ取得 (裁定ログ#6 次アクション)

サーバ側 LMA 事前選別 d_lin < 25 pc (本計算の判定対象 R≤5 pc に対し
誤差 MC・軌道曲率・個別ホライズンの余裕を5倍で確保)。
視差ゼロ点 (Lindegren+21) は取込後にパイプライン側で適用 (余裕幅が吸収)。

列: 6D+誤差+5×5相関 (誤差MC)、G/BP-RP/RP (gaiaunlimited 選択関数の引数)、
ruwe/rv_nb_transits/rv_template_teff (検疫・RVS温度範囲フラグ)。
"""

import pathlib

from astroquery.gaia import Gaia

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

COLS = ("source_id, ra, dec, ra_error, dec_error, parallax, parallax_error, "
        "pmra, pmra_error, pmdec, pmdec_error, radial_velocity, "
        "radial_velocity_error, phot_g_mean_mag, phot_rp_mean_mag, bp_rp, "
        "ruwe, rv_nb_transits, rv_template_teff, "
        "ra_dec_corr, ra_parallax_corr, ra_pmra_corr, ra_pmdec_corr, "
        "dec_parallax_corr, dec_pmra_corr, dec_pmdec_corr, "
        "parallax_pmra_corr, parallax_pmdec_corr, pmra_pmdec_corr")

LMA = ("(1000*4.74047*sqrt(pmra*pmra+pmdec*pmdec)/power(parallax,2)) / "
       "sqrt((pmra*pmra+pmdec*pmdec)*power(4.74047/parallax,2) "
       "+ radial_velocity*radial_velocity)")

q = (f"SELECT {COLS} FROM gaiadr3.gaia_source "
     f"WHERE parallax > 0 AND radial_velocity IS NOT NULL AND {LMA} < 25")

job = Gaia.launch_job_async(q, background=False)
df = job.get_results().to_pandas()
dst = OUT / "dr3_candidates_lma25.parquet"
df.to_parquet(dst)
print(f"{len(df):,} 行 -> {dst}  (期待 56,286)")

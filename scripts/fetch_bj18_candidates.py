"""BJ+18 付録 A の ADQL を同一再現し、遭遇候補 (unfiltered sample) を取得

期待値: 3,865 星 (BJ+18 §2.1)。視差ゼロ点 +0.029 mas は選別式内で使用
(列としては生値を保存し、補正はパイプライン側で明示適用)。
品質カット用列 (astrometric_chi2_al 等) と 5×5 相関を全て取得。

wake 環境で実行: ~/miniforge3/envs/wake/bin/python scripts/fetch_bj18_candidates.py
出力: data/raw/bj18_unfiltered.parquet
"""

import pathlib

from astroquery.gaia import Gaia

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

COLS = ("source_id, ra, dec, ra_error, dec_error, parallax, parallax_error, "
        "pmra, pmra_error, pmdec, pmdec_error, radial_velocity, "
        "radial_velocity_error, phot_g_mean_mag, "
        "astrometric_chi2_al, astrometric_n_good_obs_al, visibility_periods_used, "
        "ra_dec_corr, ra_parallax_corr, ra_pmra_corr, ra_pmdec_corr, "
        "dec_parallax_corr, dec_pmra_corr, dec_pmdec_corr, "
        "parallax_pmra_corr, parallax_pmdec_corr, pmra_pmdec_corr")

# BJ+18 付録 A の LMA 選別式 (d_ph^lin < 10 pc, 視差ゼロ点 +0.029 込み) を忠実に再現
LMA = ("(1000*4.74047*sqrt(pmra*pmra+pmdec*pmdec)/power(parallax+0.029,2)) / "
       "sqrt((pmra*pmra+pmdec*pmdec)*power(4.74047/(parallax+0.029),2) "
       "+ radial_velocity*radial_velocity)")

q = (f"SELECT {COLS} FROM gaiadr2.gaia_source "
     f"WHERE parallax IS NOT NULL AND parallax > -0.029 "
     f"AND radial_velocity IS NOT NULL AND {LMA} < 10")

job = Gaia.launch_job_async(q, background=False)
df = job.get_results().to_pandas()
dst = OUT / "bj18_unfiltered.parquet"
df.to_parquet(dst)
print(f"{len(df):,} 行 -> {dst}  (期待値 3,865)")

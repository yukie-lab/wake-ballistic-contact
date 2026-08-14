"""GDR2mock (Rybizki+18, GAVO TAP) から完備性計算の素材を取得 (G3-3 Stage C)

1. mock 観測側: G<=12.5 ∧ 3550<Teff<6900 (BJ+18 §4.2 のクエリ) のうち
   LMA d_lin < 15 pc (ノイズ余裕込みの緩い事前選別) — ノイズ付与は手元で実施
2. mock 局所完全サンプル: 70 pc 以内の全星 (G<20.7 で M9 級まで完備) —
   一様場の遭遇流束定数 a = (2π/V) Σ v_i の実測用
   (BJ の mock full Galaxy は Galaxia 直サンプルで a の値は非公開。
   同一銀河モデル (GDR2mock=Galaxia 系) の局所体積から解析的に再構築する)
"""

import pathlib

from astroquery.utils.tap.core import TapPlus

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)
tap = TapPlus(url="https://dc.g-vo.org/tap")

# 件数照合 (公刊 4.4M) は q1 と同時に async で実施
jobc = tap.launch_job_async("SELECT count(*) AS n FROM gdr2mock.main "
                            "WHERE phot_g_mean_mag <= 12.5 "
                            "AND teff_val > 3550 AND teff_val < 6900",
                            background=False)
print("mock 観測側母集団:", jobc.get_results()["n"][0], "(公刊 4.4M)", flush=True)

LMA = ("(1000*4.74047*sqrt(pmra*pmra+pmdec*pmdec)/power(parallax,2)) / "
       "sqrt((pmra*pmra+pmdec*pmdec)*power(4.74047/parallax,2) "
       "+ radial_velocity*radial_velocity)")

q1 = (f"SELECT ra, dec, parallax, pmra, pmdec, radial_velocity, phot_g_mean_mag "
      f"FROM gdr2mock.main "
      f"WHERE phot_g_mean_mag <= 12.5 AND teff_val > 3550 AND teff_val < 6900 "
      f"AND parallax > 0 AND {LMA} < 15")
job1 = tap.launch_job_async(q1, background=False)
df1 = job1.get_results().to_pandas()
df1.to_parquet(OUT / "gdr2mock_obs_candidates.parquet")
print(f"mock 観測側 LMA<15pc: {len(df1):,} 行")

q2 = ("SELECT ra, dec, parallax, pmra, pmdec, radial_velocity, phot_g_mean_mag "
      "FROM gdr2mock.main WHERE parallax > 14.2857")
job2 = tap.launch_job_async(q2, background=False)
df2 = job2.get_results().to_pandas()
df2.to_parquet(OUT / "gdr2mock_local70pc.parquet")
print(f"mock 局所 70 pc: {len(df2):,} 行")

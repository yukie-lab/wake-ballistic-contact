"""Gaia DR2 の RV 保有星 (7,224,631) を取得 — G3-3 の同一入力 (BJ+18 再現)

wake 環境で実行: ~/miniforge3/envs/wake/bin/python scripts/fetch_dr2_rv.py
random_index で 8 チャンクに分割し、data/raw/dr2_rv_XX.parquet に保存。
"""

import pathlib
import time

from astroquery.gaia import Gaia

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

COLS = ("source_id, ra, dec, parallax, parallax_error, pmra, pmra_error, "
        "pmdec, pmdec_error, radial_velocity, radial_velocity_error, "
        "phot_g_mean_mag, ra_dec_corr, ra_parallax_corr, ra_pmra_corr, "
        "ra_pmdec_corr, dec_parallax_corr, dec_pmra_corr, dec_pmdec_corr, "
        "parallax_pmra_corr, parallax_pmdec_corr, pmra_pmdec_corr")

N_TOTAL_INDEX = 1_692_919_135  # DR2 gaia_source 総行数
N_CHUNKS = 8

total = 0
for i in range(N_CHUNKS):
    dst = OUT / f"dr2_rv_{i:02d}.parquet"
    if dst.exists():
        print(f"[{i}] skip (exists)", flush=True)
        continue
    lo = i * (N_TOTAL_INDEX // N_CHUNKS)
    hi = (i + 1) * (N_TOTAL_INDEX // N_CHUNKS) - 1 if i < N_CHUNKS - 1 else N_TOTAL_INDEX
    q = (f"SELECT {COLS} FROM gaiadr2.gaia_source "
         f"WHERE radial_velocity IS NOT NULL "
         f"AND random_index BETWEEN {lo} AND {hi}")
    t0 = time.time()
    job = Gaia.launch_job_async(q, background=False)
    tab = job.get_results()
    df = tab.to_pandas()
    df.to_parquet(dst)
    total += len(df)
    print(f"[{i}] {len(df):,} 行 ({time.time() - t0:.0f} s) -> {dst.name}", flush=True)

print(f"完了: 追加 {total:,} 行", flush=True)

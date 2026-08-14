"""GAVO TAP への UWS 直接クライアント (ジョブフェーズ可視化付き)

astroquery の launch_job_async はフェーズが見えないため、requests で
/tap/async を直接叩き、QUEUED/EXECUTING/COMPLETED/ERROR を逐次ログする。
COMPLETED で votable を取得し parquet 保存。

使い方: python scripts/gavo_uws.py <q1|q2>
"""

import pathlib
import sys
import time

import requests
from astropy.io.votable import parse_single_table
import io

BASE = "https://dc.g-vo.org/tap"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

LMA = ("(1000*4.74047*sqrt(pmra*pmra+pmdec*pmdec)/power(parallax,2)) / "
       "sqrt((pmra*pmra+pmdec*pmdec)*power(4.74047/parallax,2) "
       "+ radial_velocity*radial_velocity)")

QUERIES = {
    "q1": (
        f"SELECT ra, dec, parallax, pmra, pmdec, radial_velocity, phot_g_mean_mag "
        f"FROM gdr2mock.main "
        f"WHERE phot_g_mean_mag <= 12.5 AND teff_val > 3550 AND teff_val < 6900 "
        f"AND parallax > 0 AND {LMA} < 15",
        "gdr2mock_obs_candidates.parquet"),
    "q2": (
        "SELECT ra, dec, parallax, pmra, pmdec, radial_velocity, phot_g_mean_mag "
        "FROM gdr2mock.main WHERE parallax > 14.2857",
        "gdr2mock_local70pc.parquet"),
}


def run(name):
    query, fname = QUERIES[name]
    r = requests.post(f"{BASE}/async", data={
        "REQUEST": "doQuery", "LANG": "ADQL", "QUERY": query,
        "FORMAT": "votable", "MAXREC": "20000000",
    }, allow_redirects=False, timeout=60)
    job_url = r.headers["Location"]
    print(f"[{name}] job: {job_url}", flush=True)
    requests.post(f"{job_url}/phase", data={"PHASE": "RUN"}, timeout=60)
    last = None
    t0 = time.time()
    while True:
        ph = requests.get(f"{job_url}/phase", timeout=60).text.strip()
        if ph != last:
            print(f"[{name}] {time.time() - t0:6.0f}s  phase={ph}", flush=True)
            last = ph
        if ph in ("COMPLETED", "ERROR", "ABORTED"):
            break
        time.sleep(20)
    if ph != "COMPLETED":
        err = requests.get(f"{job_url}/error", timeout=60).text[:2000]
        print(f"[{name}] エラー詳細:\n{err}", flush=True)
        return 1
    res = requests.get(f"{job_url}/results/result", timeout=600)
    tab = parse_single_table(io.BytesIO(res.content)).to_table()
    df = tab.to_pandas()
    df.to_parquet(OUT / fname)
    print(f"[{name}] {len(df):,} 行 -> {fname}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))

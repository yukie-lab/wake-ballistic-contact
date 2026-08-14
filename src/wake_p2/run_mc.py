"""Phase 2 誤差 MC 本計算 (PHASES 1.2 Phase 2 作業項目1)

- 全候補 56,286 星 × 2000 サロゲート (5×5 天文測量共分散 + 独立 RV)
- MWPotential2014 (主経路)・WAKE 既定太陽パラメータ
- 星順序はシャッフル済みチャンク (~1000 星): 先頭チャンク群が母集団の
  代表標本になる → 冒頭 5% 定常性速報 (裁定ログ#6 運用条項) の設計前提
- workers=6 (憲法第2条4項)。チャンクごとに npz 保存 (中断再開可)

実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/run_mc.py
出力: data/p2/mc/chunk_XXX.npz
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
from concurrent.futures import ProcessPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
MC = P2 / "mc"
N_SURR = 2000
CHUNK = 1000
SHUFFLE_SEED = 20260814


def _load():
    z = np.load(P2 / "catalog_ingested.npz")
    return {k: z[k] for k in z.files}


def _lma_t(d):
    from wake_data.icrs import icrs_to_helio_galactic
    pos, vel = icrs_to_helio_galactic(d["ra"], d["dec"], d["parallax"],
                                      d["pmra"], d["pmdec"], d["radial_velocity"])
    v = vel * 1.02271
    vv = np.einsum("ij,ij->i", v, v)
    return -np.einsum("ij,ij->i", pos, v) / np.maximum(vv, 1e-30)


def _surrogates(d, idx, rng):
    """5×5 天文測量共分散 + 独立 RV (run_g33 と同構成; npz 入力版)。"""
    n = len(idx)
    err = np.stack([d["ra_error"][idx], d["dec_error"][idx],
                    d["parallax_error"][idx], d["pmra_error"][idx],
                    d["pmdec_error"][idx]], axis=1)
    corr = np.zeros((n, 5, 5))
    corr[:, np.arange(5), np.arange(5)] = 1.0
    pairs = {(0, 1): "corr_ra_dec", (0, 2): "corr_ra_parallax",
             (0, 3): "corr_ra_pmra", (0, 4): "corr_ra_pmdec",
             (1, 2): "corr_dec_parallax", (1, 3): "corr_dec_pmra",
             (1, 4): "corr_dec_pmdec", (2, 3): "corr_parallax_pmra",
             (2, 4): "corr_parallax_pmdec", (3, 4): "corr_pmra_pmdec"}
    for (i, j), c in pairs.items():
        corr[:, i, j] = corr[:, j, i] = d[c][idx]
    cov = corr * err[:, :, None] * err[:, None, :]
    L = np.linalg.cholesky(cov + 1e-10 * np.eye(5))
    delta = np.einsum("nij,nsj->nsi", L, rng.standard_normal((n, N_SURR, 5)))
    dec0 = d["dec"][idx][:, None]
    ra = d["ra"][idx][:, None] + delta[:, :, 0] / 3.6e6 / np.cos(np.radians(dec0))
    dec = dec0 + delta[:, :, 1] / 3.6e6
    plx = d["parallax"][idx][:, None] + delta[:, :, 2]
    pmra = d["pmra"][idx][:, None] + delta[:, :, 3]
    pmdec = d["pmdec"][idx][:, None] + delta[:, :, 4]
    rv = (d["radial_velocity"][idx][:, None]
          + rng.standard_normal((n, N_SURR)) * d["rv_error"][idx][:, None])
    return ra, dec, plx, pmra, pmdec, rv


def run_chunk(args):
    ci, idx = args
    dst = MC / f"chunk_{ci:03d}.npz"
    if dst.exists():
        return ci, 0.0, "skip"
    from wake_data.icrs import icrs_to_helio_galactic
    from wake_engine import MWPotential2014
    from wake_engine.coords import helio_galactic_to_engine
    from wake_engine.integrate import closest_approach
    t0 = time.time()
    d = _load()
    pot = MWPotential2014()
    rng = np.random.default_rng(100000 + ci)
    ra, dec, plx, pmra, pmdec, rv = _surrogates(d, idx, rng)
    t_lin = _lma_t(d)[idx]
    n = len(idx)
    t_ph = np.full((n, N_SURR), np.nan, dtype=np.float32)
    d_ph = np.full((n, N_SURR), np.nan, dtype=np.float32)
    edge = np.zeros((n, N_SURR), dtype=bool)
    abs_t = np.abs(t_lin)
    for lo, hi in [(0, 3), (3, 6), (6, 12), (12, 20), (20, np.inf)]:
        gsel = np.flatnonzero((abs_t >= lo) & (abs_t < hi))
        if not len(gsel):
            continue
        window = max(13.0, min(2.2 * (hi if np.isfinite(hi)
                                      else abs_t[gsel].max() * 1.05), 45.0))
        dt = window / 2400.0
        fl = (gsel[:, None] * N_SURR + np.arange(N_SURR)).ravel()
        ok = plx.ravel()[fl] > 0
        use = fl[ok]
        pos, vel = icrs_to_helio_galactic(
            ra.ravel()[use], dec.ravel()[use], plx.ravel()[use],
            pmra.ravel()[use], pmdec.ravel()[use], rv.ravel()[use])
        for s in range(0, len(use), 400_000):
            sl = slice(s, s + 400_000)
            pe, ve = helio_galactic_to_engine(pot, pos[sl], vel[sl])
            enc = closest_approach(pot, pe, ve, window=window, dt=dt)
            t_ph.ravel()[use[sl]] = enc.t_min
            d_ph.ravel()[use[sl]] = enc.d_min * 1e3
            edge.ravel()[use[sl]] = enc.at_edge
    np.savez_compressed(dst, star_idx=idx, t_ph=t_ph, d_ph=d_ph, edge=edge)
    return ci, time.time() - t0, "done"


def main():
    MC.mkdir(parents=True, exist_ok=True)
    d = _load()
    n = len(d["source_id"])
    rng = np.random.default_rng(SHUFFLE_SEED)
    order = rng.permutation(n)
    chunks = [(ci, order[s:s + CHUNK])
              for ci, s in enumerate(range(0, n, CHUNK))]
    print(f"{n} 星 / {len(chunks)} チャンク / workers=6", flush=True)
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=6) as pool:
        for ci, el, st in pool.map(run_chunk, chunks):
            done += 1
            print(f"chunk {ci:03d} {st} ({el:.0f}s) [{done}/{len(chunks)} "
                  f"経過 {time.time() - t0:.0f}s]", flush=True)
    print("本計算完了", flush=True)


if __name__ == "__main__":
    main()

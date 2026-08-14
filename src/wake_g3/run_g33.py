"""G3-3 本実行 — BJ+18 同一手法・同一入力の段階実行

Stage A: 品質カットと公刊数値の照合 (3865 → 3465 → 3379, G<12.5 = 2522)
Stage B: サロゲート 2000/星 × 軌道積分 (DC95, BJ 太陽パラメータ) → 星別要約
         照合: Table 1 の d_ph^med 閾値別星数 / P(<1pc)>0.5 = 31(bogus込み) / Gl710
Stage C: 完備性 C(t,d) と頻度 (run_g33_rate.py — GDR2mock 取得後)

使い方: python3 src/wake_g3/run_g33.py A     (または B)
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_engine import DC95Potential, KMS
from wake_engine.coords import helio_galactic_to_engine
from wake_engine.integrate import closest_approach
from wake_data.icrs import icrs_to_helio_galactic
from wake_g3.g33_pipeline import lma_perihelion

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "g33"

# BJ+18 の太陽パラメータ (Paper 1 §3.3): r☉=8 kpc, z☉=+10 pc,
# (U, V_total, W)☉ = (11.1, 242, 7.25) km/s。エンジン系: x 反銀河中心 → vx=-U
BJ_SUN = (np.array([8.0, 0.0, 0.010]),
          np.array([-11.1 * KMS, 242 * KMS, 7.25 * KMS]))
PLX_ZP = 0.029  # mas (Lindegren+18 / BJ18 §2.1)
N_SURR = 2000


def load_filtered(verbose=True):
    import pandas as pd
    df = pd.read_parquet(RAW / "bj18_unfiltered.parquet")
    n0 = len(df)
    # 視差ゼロ点補正 (明示適用)
    df["parallax"] = df["parallax"] + PLX_ZP
    # u < 35
    u = np.sqrt(df["astrometric_chi2_al"]
                / (df["astrometric_n_good_obs_al"] - 5))
    cut_u = u < 35
    cut_vis = df["visibility_periods_used"] >= 8
    n1 = int(cut_u.sum())
    n2 = int((cut_u & cut_vis).sum())
    # 中間段階の照合: u<35 は 3456 vs 公刊 3465 (9星差)。この9星は vis<8 と
    # 重複しているかを検査 — 重複なら最終サンプルは影響を受けない
    n_boundary = int((~cut_u & ~cut_vis).sum())
    df = df[cut_u & cut_vis]
    n_bright = int((df["phot_g_mean_mag"] < 12.5).sum())
    if verbose:
        print(f"unfiltered {n0} (公刊 3865) → u<35: {n1} (公刊 3465) → "
              f"vis≥8: {n2} (公刊 3379) / G<12.5: {n_bright} (公刊 2522)")
        print(f"  [注] u カット除外のうち vis<8 と重複: {n_boundary} 星 "
              f"(u<35 中間値の 9 星差はカット順序/境界の差 — 最終値は完全一致)")
        assert (n0, n2, n_bright) == (3865, 3379, 2522), \
            "最終サンプルが公刊数値と不一致 — 停止して照合 (裁定5 プロトコル)"
    return df.reset_index(drop=True)


def stage_a():
    df = load_filtered()
    d = {k: df[k].to_numpy() for k in df.columns}
    d["radial_velocity"] = d["radial_velocity"].astype(float)
    t_lin, d_lin = lma_perihelion(d)
    print(f"LMA: |t_lin| 中央値 {np.median(np.abs(t_lin)):.2f} Myr / "
          f"最大 {np.max(np.abs(t_lin)):.1f} Myr, d_lin<10pc: {(d_lin < 10).sum()}")
    return df


def sample_surrogates_5x5(df, n_surr, rng):
    """5×5 天文測量共分散 + 独立 RV のサロゲート (BJ+18 と同構成)。"""
    n = len(df)
    g = lambda c: df[c].to_numpy(float)
    err = np.stack([g("ra_error"), g("dec_error"), g("parallax_error"),
                    g("pmra_error"), g("pmdec_error")], axis=1)  # mas 系
    names = ["ra", "dec", "parallax", "pmra", "pmdec"]
    corr = np.zeros((n, 5, 5))
    corr[:, np.arange(5), np.arange(5)] = 1.0
    pairs = {(0, 1): "ra_dec_corr", (0, 2): "ra_parallax_corr",
             (0, 3): "ra_pmra_corr", (0, 4): "ra_pmdec_corr",
             (1, 2): "dec_parallax_corr", (1, 3): "dec_pmra_corr",
             (1, 4): "dec_pmdec_corr", (2, 3): "parallax_pmra_corr",
             (2, 4): "parallax_pmdec_corr", (3, 4): "pmra_pmdec_corr"}
    for (i, j), c in pairs.items():
        corr[:, i, j] = corr[:, j, i] = g(c)
    cov = corr * err[:, :, None] * err[:, None, :]
    L = np.linalg.cholesky(cov + 1e-10 * np.eye(5))
    z = rng.standard_normal((n, n_surr, 5))
    delta = np.einsum("nij,nsj->nsi", L, z)   # [Δra*, Δdec, Δplx, Δpmra, Δpmdec]
    dec0 = g("dec")[:, None]
    ra = g("ra")[:, None] + delta[:, :, 0] / 3.6e6 / np.cos(np.radians(dec0))
    dec = dec0 + delta[:, :, 1] / 3.6e6
    plx = g("parallax")[:, None] + delta[:, :, 2]
    pmra = g("pmra")[:, None] + delta[:, :, 3]
    pmdec = g("pmdec")[:, None] + delta[:, :, 4]
    rv = (g("radial_velocity")[:, None]
          + rng.standard_normal((n, n_surr)) * g("radial_velocity_error")[:, None])
    return ra, dec, plx, pmra, pmdec, rv


def stage_b():
    df = load_filtered()
    d = {k: df[k].to_numpy() for k in df.columns}
    t_lin, d_lin = lma_perihelion(d)
    rng = np.random.default_rng(2018)
    ra, dec, plx, pmra, pmdec, rv = sample_surrogates_5x5(df, N_SURR, rng)
    n = len(df)
    t_ph = np.full((n, N_SURR), np.nan, dtype=np.float32)
    d_ph = np.full((n, N_SURR), np.nan, dtype=np.float32)
    edge = np.zeros((n, N_SURR), dtype=bool)
    n_rej = int((plx <= 0).sum())  # 負視差サロゲート棄却 (Paper 1 準拠、件数記録)
    pot = DC95Potential()

    # |t_lin| で窓グループ化 (BJ は星ごとに 2·t_lin^lin を 1000 步。
    # 本実装はグループ上限の 2.2 倍窓 × 2000 步 — 分解能は BJ の約2倍)
    abs_t = np.abs(t_lin)
    bounds = [0, 2.5, 5, 10, 25, 50, 100, 200, np.inf]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        gsel = np.flatnonzero((abs_t >= lo) & (abs_t < hi))
        if len(gsel) == 0:
            continue
        window = 2.2 * (hi if np.isfinite(hi) else abs_t[gsel].max() * 1.05)
        window = max(window, 6.0)
        dt = window / 2000.0
        idx_flat = (gsel[:, None] * N_SURR + np.arange(N_SURR)).ravel()
        ok = plx.ravel()[idx_flat] > 0
        use = idx_flat[ok]
        pos, vel = icrs_to_helio_galactic(
            ra.ravel()[use], dec.ravel()[use], plx.ravel()[use],
            pmra.ravel()[use], pmdec.ravel()[use], rv.ravel()[use])
        for s in range(0, len(use), 400_000):
            sl = slice(s, s + 400_000)
            pe, ve = helio_galactic_to_engine(pot, pos[sl], vel[sl], sun=BJ_SUN)
            enc = closest_approach(pot, pe, ve, window=window, dt=dt, sun=BJ_SUN)
            t_ph.ravel()[use[sl]] = enc.t_min
            d_ph.ravel()[use[sl]] = enc.d_min * 1e3
            edge.ravel()[use[sl]] = enc.at_edge
        print(f"  窓グループ |t_lin|∈[{lo},{hi}) : {len(gsel)} 星 "
              f"(window ±{window:.0f} Myr, dt {dt:.3f})", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "surrogate_perihelia.npz",
                        source_id=d["source_id"], t_ph=t_ph, d_ph=d_ph,
                        edge=edge, g_mag=d["phot_g_mean_mag"],
                        n_rejected_negplx=n_rej)
    print(f"負視差棄却サロゲート: {n_rej}")

    # 照合: Table 1 (d_ph^med 閾値別星数)
    d_med = np.nanmedian(d_ph, axis=1)
    print("\nd_ph^med 閾値別星数 (公刊: 10:2548 / 5:694 / 3:283 / 2:129 / 1:31 / 0.5:8 / 0.25:3)")
    for th, pub in [(10, 2548), (5, 694), (3, 283), (2, 129), (1, 31),
                    (0.5, 8), (0.25, 3)]:
        print(f"  d<{th:>5}: {int((d_med < th).sum()):>5} (公刊 {pub})")
    p1 = np.nanmean(d_ph < 1.0, axis=1)
    print(f"P(d_ph<1pc)>0.5: {int((p1 > 0.5).sum())} (公刊 31, bogus除去後 26)")
    gj = d["source_id"] == 4270814637616488064
    if gj.any():
        i = np.flatnonzero(gj)[0]
        tq = np.nanpercentile(t_ph[i], [5, 50, 95])
        dq = np.nanpercentile(d_ph[i], [5, 50, 95])
        print(f"Gl710 (DR2): t_med {tq[1]*1e3:.0f} kyr (CI90 {tq[0]*1e3:.0f}-{tq[2]*1e3:.0f}) "
              f"/ d_med {dq[1]:.4f} pc (CI90 {dq[0]:.4f}-{dq[2]:.4f}) "
              f"[BJ18公刊: 1281 kyr / 0.0676 (0.0519-0.0842)]")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "A"
    {"A": stage_a, "B": stage_b}[stage]()

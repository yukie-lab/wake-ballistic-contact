"""G3-3 パイプライン: BJ+18 同一手法・同一入力の接近頻度再現

段階:
  1. DR2 RV 保有星 7,224,631 の読込 (GaiaDR2FileProvider)
  2. LMA 予備選別 (閉形式・公称値): d_ph^lin < d_max の候補抽出
  3. 候補星のサロゲート積分: (parallax, pmra, pmdec) 3×3 相関 + RV 独立の
     誤差サンプリング → 軌道積分 → 星ごとの (t_ph, d_ph) 事後分布
     (位置誤差は寄与 ~1e-5 pc のため省略 — BJ18 の 5×5 との差は無視可能、報告に明記)
  4. 観測遭遇流束 F_obs と完備性補正 → 頻度 (パラメータは BJ18 詳細抽出後に固定)

窓端の扱い: at_edge 星は「判定不能」会計へ (憲法第5条6項)。
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.icrs import icrs_to_helio_galactic
from wake_engine import closest_approach
from wake_engine.coords import helio_galactic_to_engine

PC_PER_MYR = 1.02271


def lma_perihelion(data):
    """全星の LMA 近日点 (公称値、閉形式)。戻り値: t_lin [Myr], d_lin [pc]。"""
    pos, vel = icrs_to_helio_galactic(
        data["ra"], data["dec"], data["parallax"],
        data["pmra"], data["pmdec"], data["radial_velocity"])
    v = vel * PC_PER_MYR                       # pc/Myr
    vv = np.einsum("ij,ij->i", v, v)
    tca = -np.einsum("ij,ij->i", pos, v) / np.maximum(vv, 1e-30)
    dmin = np.linalg.norm(pos + v * tca[:, None], axis=1)
    return tca, dmin


def prefilter(data, d_max_pc=10.0, t_max_myr=15.0, parallax_min=0.0):
    """LMA 予備選別。視差が正でない星は候補から外す (距離が定義できない)。"""
    t_lin, d_lin = lma_perihelion(data)
    ok = ((data["parallax"] > parallax_min)
          & (d_lin < d_max_pc) & (np.abs(t_lin) < t_max_myr))
    return ok, t_lin, d_lin


def sample_surrogates(data, idx, n_surr, rng):
    """候補星 idx のサロゲート観測量を生成。
    (parallax, pmra, pmdec) は 3×3 相関、RV は独立ガウス。
    戻り値: 各 (n_star, n_surr) の parallax/pmra/pmdec/rv。"""
    n = len(idx)
    e_p = data["parallax_error"][idx]
    e_a = data["pmra_error"][idx]
    e_d = data["pmdec_error"][idx]
    c_pa = data["corr_parallax_pmra"][idx]
    c_pd = data["corr_parallax_pmdec"][idx]
    c_ad = data["corr_pmra_pmdec"][idx]
    cov = np.zeros((n, 3, 3))
    cov[:, 0, 0] = e_p ** 2
    cov[:, 1, 1] = e_a ** 2
    cov[:, 2, 2] = e_d ** 2
    cov[:, 0, 1] = cov[:, 1, 0] = c_pa * e_p * e_a
    cov[:, 0, 2] = cov[:, 2, 0] = c_pd * e_p * e_d
    cov[:, 1, 2] = cov[:, 2, 1] = c_ad * e_a * e_d
    # 数値対称性の保険
    L = np.linalg.cholesky(cov + 1e-12 * np.eye(3))
    z = rng.standard_normal((n, n_surr, 3))
    delta = np.einsum("nij,nsj->nsi", L, z)
    plx = data["parallax"][idx][:, None] + delta[:, :, 0]
    pmra = data["pmra"][idx][:, None] + delta[:, :, 1]
    pmdec = data["pmdec"][idx][:, None] + delta[:, :, 2]
    rv = (data["radial_velocity"][idx][:, None]
          + rng.standard_normal((n, n_surr)) * data["rv_error"][idx][:, None])
    return plx, pmra, pmdec, rv


def surrogate_encounters(data, idx, potential, n_surr=2000, window=10.0,
                         dt=0.01, seed=1, batch=200_000):
    """候補星のサロゲートを軌道積分し、星ごとの (t_ph, d_ph) 分布を返す。

    負視差サロゲートは棄却してその星の分布から除外 (BJ 系の標準)。
    戻り値: t_ph (n_star, n_surr), d_ph (n_star, n_surr) — 棄却は NaN、
            at_edge (n_star, n_surr) bool。
    """
    rng = np.random.default_rng(seed)
    plx, pmra, pmdec, rv = sample_surrogates(data, idx, n_surr, rng)
    n_star = len(idx)
    ra = np.repeat(data["ra"][idx], n_surr)
    dec = np.repeat(data["dec"][idx], n_surr)
    flat = dict(plx=plx.ravel(), pmra=pmra.ravel(), pmdec=pmdec.ravel(),
                rv=rv.ravel())
    valid = flat["plx"] > 0
    t_ph = np.full(n_star * n_surr, np.nan)
    d_ph = np.full(n_star * n_surr, np.nan)
    at_edge = np.zeros(n_star * n_surr, dtype=bool)
    vidx = np.flatnonzero(valid)
    for s in range(0, len(vidx), batch):
        sl = vidx[s:s + batch]
        pos, vel = icrs_to_helio_galactic(ra[sl], dec[sl], flat["plx"][sl],
                                          flat["pmra"][sl], flat["pmdec"][sl],
                                          flat["rv"][sl])
        pe, ve = helio_galactic_to_engine(potential, pos, vel)
        enc = closest_approach(potential, pe, ve, window=window, dt=dt)
        t_ph[sl] = enc.t_min
        d_ph[sl] = enc.d_min * 1e3
        at_edge[sl] = enc.at_edge
    shape = (n_star, n_surr)
    return t_ph.reshape(shape), d_ph.reshape(shape), at_edge.reshape(shape)


def star_summary(t_ph, d_ph):
    """星ごとの要約: 中央値と P(d_ph < r)。NaN (棄却サロゲート) は除外。"""
    med_t = np.nanmedian(t_ph, axis=1)
    med_d = np.nanmedian(d_ph, axis=1)
    p1 = np.nanmean(d_ph < 1.0, axis=1)
    p5 = np.nanmean(d_ph < 5.0, axis=1)
    return {"t_med": med_t, "d_med": med_d, "p_lt1pc": p1, "p_lt5pc": p5}

"""到来イベント運動学の抽出(Phase 3 地図生成の入力)

クリーン母集団の到来寄与星ごとに: 速度 [km/s]・アンカー半径 {1,2,5} pc での
λ 寄与係数(w·n/e/N_SURR)を抽出。星単位ブートストラップでクリーン λ の CI も算出
(地図境界の MC 収束 — Phase 3 出口 G1 の材料)。

実行: python3 src/wake_p3/arrival_kinematics.py → data/p3/arrival_kinematics.npz
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR
from wake_data.horizon_eff import effective_horizons
from wake_data.icrs import icrs_to_helio_galactic

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
P3 = ROOT / "data" / "p3"
N_SURR = 2000
N_BOOT = 2000


def main():
    cat = np.load(P2 / "catalog_ingested.npz")
    b5 = np.load(P2 / "quarantine_bit5.npz")["mask"]
    S = cat["s_completeness"]
    th, _ = effective_horizons(cat)
    n_cat = len(S)
    c1 = np.zeros(n_cat)
    c2 = np.zeros(n_cat)
    c5 = np.zeros(n_cat)
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR) & ~b5[idx]
        w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0)
        e = 2.0 * np.minimum(10.0, np.maximum(th_c, 1e-9))
        base = (np.isfinite(t_ph) & ~edge & (np.abs(t_ph) <= 10.0)
                & (np.abs(t_ph) <= th_c[:, None]))
        for dmax, acc in ((1.0, c1), (2.0, c2), (5.0, c5)):
            n = (base & (d_ph < dmax)).sum(axis=1)
            acc[idx] += w * n / e / N_SURR
    contrib = np.flatnonzero(c5 > 0)
    ok = cat["parallax"][contrib] > 0
    contrib = contrib[ok]
    pos, vel = icrs_to_helio_galactic(
        cat["ra"][contrib], cat["dec"][contrib], cat["parallax"][contrib],
        cat["pmra"][contrib], cat["pmdec"][contrib],
        cat["radial_velocity"][contrib])
    # クリーン λ の星単位ブートストラップ CI
    rng = np.random.default_rng(88)
    lam = {}
    ci = {}
    for name, c in (("1pc", c1), ("2pc", c2), ("5pc", c5)):
        cc = c[contrib]
        lam[name] = float(cc.sum())
        k = len(cc)
        boots = np.array([cc[rng.integers(0, k, k)].sum() for _ in range(N_BOOT)])
        ci[name] = (float(np.quantile(boots, 0.025)),
                    float(np.quantile(boots, 0.975)), float(boots.std()))
    P3.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(P3 / "arrival_kinematics.npz",
                        star_idx=contrib, vel_kms=vel, pos_pc=pos,
                        c1=c1[contrib], c2=c2[contrib], c5=c5[contrib],
                        lam1=lam["1pc"], lam2=lam["2pc"], lam5=lam["5pc"],
                        ci1=ci["1pc"], ci2=ci["2pc"], ci5=ci["5pc"])
    print(f"寄与星 {len(contrib):,} / クリーン λ: "
          f"1pc {lam['1pc']:.2f} [{ci['1pc'][0]:.2f},{ci['1pc'][1]:.2f}] / "
          f"2pc {lam['2pc']:.1f} / 5pc {lam['5pc']:.1f}")


if __name__ == "__main__":
    main()

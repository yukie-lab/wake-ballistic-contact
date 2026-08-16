"""t_pot 第3ホライズン(裁定ログ#11 裁定2)

定義(v2 — CI 予算基準と整合): 2種ポテンシャルでの名目軌道の乖離
|x_A(t) − x_B(t)| が、その星の**測定不確かさ成長 σ_v·|t|**(σ_v = d_th/t_h_meas)
を最初に上回る |t|。すなわち「モデル系統が測定誤差を追い越す時刻」。
実効ホライズン = min(t_h_meas, t_pot) — モデル不確かさを測定不確かさと同格に扱う
(非対称原理)。小 |t| では乖離が二次・測定が一次成長のため自然に発火しない。
(v1 の d_th 固定閾値は高精度星の予算超過を捕捉できず廃止 — 監査で検出)

出力: data/p2/horizon_eff.npz(t_pot25, t_pot50, t_h_eff_default, t_h_eff_sens)
実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/horizon_tpot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
SIDE = P2 / "horizon_eff.npz"
T_MAX = 13.0
DT = 0.01


def divergence_first_crossing():
    from wake_data.icrs import icrs_to_helio_galactic
    from wake_engine import MWPotential2014
    from wake_engine.coords import helio_galactic_to_engine
    from wake_engine.mcmillan_tab import McMillan17Tabulated

    cat = np.load(P2 / "catalog_ingested.npz")
    ok = cat["parallax"] > 0
    pos, vel = icrs_to_helio_galactic(cat["ra"][ok], cat["dec"][ok],
                                      cat["parallax"][ok], cat["pmra"][ok],
                                      cat["pmdec"][ok], cat["radial_velocity"][ok])
    n_cat = len(cat["parallax"])
    pa = MWPotential2014()
    pb = McMillan17Tabulated()
    # σ_v [pc/Myr] = d_th/t_h(測定ホライズンの定義の逆算)
    sig_v = 2.5 / np.maximum(cat["t_h_default"][ok], 1e-9)
    t25 = np.full(n_cat, np.inf)
    t50 = np.full(n_cat, np.inf)
    gi = np.flatnonzero(ok)

    for sign in (+1.0, -1.0):
        # 両ポテンシャルを同時にリープフロッグ(太陽も各系で整合伝播)
        PA, VA = helio_galactic_to_engine(pa, pos, vel)
        PB, VB = helio_galactic_to_engine(pb, pos, vel)
        from wake_engine.integrate import sun_state as _ss  # noqa: F401
        from wake_engine import sun_state
        spA, svA = sun_state(pa)
        spB, svB = sun_state(pb)
        XA = np.vstack([spA[None], PA])
        VAf = np.vstack([svA[None], VA])
        XB = np.vstack([spB[None], PB])
        VBf = np.vstack([svB[None], VB])
        h = sign * DT
        aA = pa.accel(XA)
        aB = pb.accel(XB)
        found25 = np.zeros(len(PA), bool)
        found50 = np.zeros(len(PA), bool)
        nstep = int(round(T_MAX / DT))
        for k in range(nstep):
            VAf += 0.5 * h * aA
            XA += h * VAf
            aA = pa.accel(XA)
            VAf += 0.5 * h * aA
            VBf += 0.5 * h * aB
            XB += h * VBf
            aB = pb.accel(XB)
            VBf += 0.5 * h * aB
            # 太陽相対位置の乖離 [pc]
            relA = (XA[1:] - XA[0]) * 1e3
            relB = (XB[1:] - XB[0]) * 1e3
            div = np.linalg.norm(relA - relB, axis=1)
            t_now = (k + 1) * DT
            thresh = sig_v * t_now
            new25 = (div >= thresh) & ~found25
            new50 = (div >= 2.0 * thresh) & ~found50
            if new25.any():
                t25[gi[new25]] = np.minimum(t25[gi[new25]], t_now)
                found25 |= new25
            if new50.any():
                t50[gi[new50]] = np.minimum(t50[gi[new50]], t_now)
                found50 |= new50
            if found50.all():
                break
    return t25, t50, cat


def main():
    t25, t50, cat = divergence_first_crossing()
    th_d, th_s = cat["t_h_default"], cat["t_h_sens"]
    eff_d = np.minimum(th_d, t25)
    eff_s = np.minimum(th_s, t50)
    np.savez_compressed(SIDE, t_pot25=t25, t_pot50=t50,
                        t_h_eff_default=eff_d, t_h_eff_sens=eff_s)
    n_bind = int((t25 < th_d).sum())
    fin = np.isfinite(t25)
    print(f"t_pot25: 有限 {fin.sum():,} 星 / 拘束(t_pot<t_h_meas) {n_bind:,} 星 "
          f"({n_bind/len(t25):.1%})")
    if fin.any():
        print(f"t_pot25 分位: p5={np.nanpercentile(np.where(fin, t25, np.nan), 5):.1f} "
              f"median={np.nanpercentile(np.where(fin, t25, np.nan), 50):.1f} Myr")
    print(f"→ {SIDE}")


if __name__ == "__main__":
    main()

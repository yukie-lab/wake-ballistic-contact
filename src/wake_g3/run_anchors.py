"""G3-1 / G3-2 アンカー本実行 (固定入力再現テスト)

各入力セットを誤差 MC (N=2000, 対角近似) で伝播し、t_ph / d_ph の
中央値と CI90 を参照論文の目標値・裁定済み合格帯と突き合わせる。

ポテンシャル: DC95 (BJ 同一入力の原則) と MWPotential2014 (主計算系) の両方で
実行し、ポテンシャル差も同時に見る (2種監査の前哨)。

実行: python3 src/wake_g3/run_anchors.py
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.icrs import icrs_to_helio_galactic
from wake_engine import MWPotential2014, DC95Potential, closest_approach
from wake_engine.coords import helio_galactic_to_engine
from wake_g3 import inputs as INP

N_SURROGATES = 2000


def run_case(case, potential, rng):
    n = N_SURROGATES
    plx = case["parallax"] + rng.normal(0, case["parallax_err"], n)
    pmra = case["pmra"] + rng.normal(0, case["pmra_err"], n)
    pmdec = case["pmdec"] + rng.normal(0, case["pmdec_err"], n)
    rv = case["rv"] + rng.normal(0, case["rv_err"], n)
    ra = np.full(n, case["ra"])
    dec = np.full(n, case["dec"])
    pos, vel = icrs_to_helio_galactic(ra, dec, plx, pmra, pmdec, rv)
    pe, ve = helio_galactic_to_engine(potential, pos, vel)
    enc = closest_approach(potential, pe, ve, window=case["window"], dt=case["dt"])
    t = enc.t_min
    d = enc.d_min * 1e3  # pc
    return {
        "t_med": float(np.median(t)),
        "t_ci90": tuple(np.percentile(t, [5, 95])),
        "d_med": float(np.median(d)),
        "d_ci90": tuple(np.percentile(d, [5, 95])),
        "edge_frac": float(enc.at_edge.mean()),
    }


def in_band(x, band):
    return band[0] <= x <= band[1]


def main():
    pots = [DC95Potential(), MWPotential2014()]
    cases = [
        ("G3-1", INP.SCHOLZ_DLFM22, "strict"),
        ("G3-1", INP.SCHOLZ_MAMAJEK15, "loose"),
        ("G3-2", INP.GJ710_BB22, "strict"),
        ("G3-2", INP.GJ710_BJ22, "strict"),
        ("G3-2", INP.GJ710_FP26, "strict"),
    ]
    print("=" * 78)
    print(f"G3-1/2 アンカー本実行 (誤差MC {N_SURROGATES} 実現・対角近似)")
    print("=" * 78)
    results = {}
    for anchor_id, case, kind in cases:
        print(f"\n--- {anchor_id} / {case['label']} [{kind}] ---")
        print(f"    目標: {case['target']}")
        for pot in pots:
            rng = np.random.default_rng(7)  # 同一サロゲートでポテンシャル比較
            r = run_case(case, pot, rng)
            unit = "kyr" if case["window"] < 1 else "Myr"
            scale = 1e3 if unit == "kyr" else 1.0
            print(f"    {pot.name:15s}: t_ph {r['t_med'] * scale:+9.1f} {unit} "
                  f"(CI90 {r['t_ci90'][0] * scale:+.1f}〜{r['t_ci90'][1] * scale:+.1f}) / "
                  f"d_ph {r['d_med']:.4f} pc (CI90 {r['d_ci90'][0]:.4f}-{r['d_ci90'][1]:.4f})"
                  + (f" / edge {r['edge_frac']:.1%}" if r["edge_frac"] > 0 else ""))
            results[(anchor_id, case["label"], pot.name)] = r

    # 帯判定 (裁定2 固定帯)
    print("\n" + "=" * 78)
    print("帯判定 (裁定ログ#4 固定帯)")
    print("=" * 78)
    verdicts = []

    r = results[("G3-1", INP.SCHOLZ_DLFM22["label"], "MWPotential2014")]
    ok_t = in_band(r["t_med"] * 1e3, (-82, -78))
    ok_d = in_band(r["d_med"], (0.31, 0.35))
    verdicts.append(("G3-1 厳格 (dlFM22系)", ok_t and ok_d,
                     f"t {r['t_med'] * 1e3:.1f} kyr∈[-82,-78]={ok_t}, "
                     f"d {r['d_med']:.3f} pc∈[0.31,0.35]={ok_d}"))

    r = results[("G3-1", INP.SCHOLZ_MAMAJEK15["label"], "MWPotential2014")]
    ok = in_band(r["t_med"] * 1e3, (-85, -60)) and in_band(r["d_med"], (0.18, 0.36))
    verdicts.append(("G3-1 緩和 (Mamajek15系)", ok,
                     f"t {r['t_med'] * 1e3:.1f} kyr, d {r['d_med']:.3f} pc"))

    for label, ci_t, ci_d in [
        (INP.GJ710_BB22["label"], (1.298, 1.350), (0.048, 0.056)),   # BB22 ±2σ / dlFM22 CI90
        (INP.GJ710_BJ22["label"], (1.257, 1.334), (0.0595, 0.0678)), # BJ22 CI90
        (INP.GJ710_FP26["label"], (1.3402, 1.3490), (0.0575, 0.0667)),  # FP26 ±2σ
    ]:
        r = results[("G3-2", label, "DC95")]
        ok_t = in_band(r["t_med"], ci_t) and in_band(r["t_med"], (1.27, 1.38))
        ok_d = in_band(r["d_med"], ci_d)
        verdicts.append((f"G3-2 厳格 ({label.split(' ')[0]})", ok_t and ok_d,
                         f"t {r['t_med']:.3f} Myr∈{ci_t}={ok_t}, "
                         f"d {r['d_med']:.4f} pc∈{ci_d}={ok_d}"))
        ok_loose = (in_band(r["t_med"], (1.24, 1.40))
                    and in_band(r["d_med"], (0.045, 0.070)))
        verdicts.append((f"G3-2 緩和 ({label.split(' ')[0]})", ok_loose,
                         f"t {r['t_med']:.3f} Myr, d {r['d_med']:.4f} pc"))

    n_fail = 0
    for name, ok, detail in verdicts:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        n_fail += 0 if ok else 1
    print("\n総合: " + ("全帯 PASS" if n_fail == 0 else
                        f"{n_fail} 件の帯不一致 — 憲法第6条: 原因究明までは上位層作業禁止"))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

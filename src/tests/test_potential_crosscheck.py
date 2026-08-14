"""ポテンシャル単点照合 (メモ2 §1 の方針 / 裁定1)

wake conda 環境 (galpy あり) で実行:
  ~/miniforge3/envs/wake/bin/python src/tests/test_potential_crosscheck.py

内容:
1. 自前 MWPotential2014 vs galpy MWPotential2014 の加速度照合 (格子点)
2. McMillan17 アダプタ: v_c(R0) が公刊値 232.8 km/s と整合するか
3. McMillan17 の Oort 定数導出 (裁定4: G2 監査ペア第2組の材料)
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_engine import MWPotential2014, McMillan17Potential, KMS


def main():
    try:
        import galpy  # noqa: F401
    except ImportError:
        print("SKIP: galpy がない環境 (wake conda 環境で実行のこと)")
        return 0
    from galpy.potential import MWPotential2014 as GalpyMW
    from galpy.potential import evaluateRforces, evaluatezforces

    failures = []

    # 1. 自前 MW2014 vs galpy MW2014
    mine = MWPotential2014()
    ro, vo = 8.0, 220.0
    conv = (vo ** 2 / ro) * KMS ** 2
    pts = [(4.0, 0.0), (8.0, 0.0), (8.0, 0.5), (12.0, -1.0), (16.0, 2.0), (2.0, 0.2)]
    max_rel = 0.0
    for R, z in pts:
        aR_g = float(evaluateRforces(GalpyMW, R / ro, z / ro)) * conv
        az_g = float(evaluatezforces(GalpyMW, R / ro, z / ro)) * conv
        a = mine.accel(np.array([[R, 0.0, z]]))[0]
        rel_R = abs(a[0] - aR_g) / abs(aR_g)
        rel_z = abs(a[2] - az_g) / max(abs(az_g), 1e-20)
        max_rel = max(max_rel, rel_R, rel_z if z != 0 else 0.0)
        print(f"  (R={R:5.1f}, z={z:+4.1f}): aR 相対差 {rel_R:.2e}"
              + (f", az 相対差 {rel_z:.2e}" if z != 0 else ""))
    print(f"[1] 自前 MW2014 vs galpy: 最大相対差 {max_rel:.2e}")
    if max_rel > 1e-3:
        failures.append(f"MW2014 照合超過: {max_rel:.2e} > 1e-3")

    # 2. McMillan17 の円速度
    mc = McMillan17Potential()
    vc = mc.vcirc(mc.R0)[0] / KMS
    print(f"[2] McMillan17 v_c({mc.R0}) = {vc:.1f} km/s (公刊 232.8)")
    if abs(vc - 232.8) > 2.0:
        failures.append(f"McMillan17 v_c 不整合: {vc:.1f}")

    # 3. McMillan17 の Oort 定数 (G2 監査ペア第2組)
    A, B, k = mc.oort_constants(mc.R0)
    print(f"[3] McMillan17 Oort: A={A:+.2f} B={B:+.2f} kappa={k:.2f} km/s/kpc")
    print("    (裁定4: この導出値を McMillan17↔エピサイクルの G2 監査ペアに使用)")

    if failures:
        print("\nFAIL:", *failures, sep="\n  - ")
        return 1
    print("\nポテンシャル単点照合: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

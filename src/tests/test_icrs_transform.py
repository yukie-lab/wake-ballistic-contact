"""ICRS→銀河変換の構造検証

方向・符号の規約バグを構造テストで潰す:
1. 銀河中心方向 (l=0, b=0) の星 → +x' (銀河中心向き)
2. l=90° の星 → +y' (回転方向)
3. 北銀極方向の星 → +z'
4. 固有運動ゼロ・RV ゼロの星 → 太陽相対速度ゼロ (太陽と共動)
5. 回転行列の直交性
6. エンジン系への写像: 銀河中心方向 d pc の星 → x_e = R0 − d/1000
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.icrs import icrs_to_helio_galactic, A_G
from wake_engine import MWPotential2014
from wake_engine.coords import helio_galactic_to_engine

# 銀河座標の基準方向 (ICRS, J2000): 銀河中心 / l=90 / 北銀極
GC_RA, GC_DEC = 266.4049882865447, -28.936177761791473
NGP_RA, NGP_DEC = 192.85948, 27.12825


def radec_of_gal_axis(row):
    """A_G の行 (銀河軸の ICRS 単位ベクトル) から ra, dec を逆算。"""
    v = A_G[row]
    dec = np.degrees(np.arcsin(v[2]))
    ra = np.degrees(np.arctan2(v[1], v[0])) % 360
    return ra, dec


def main():
    failures = []

    # 1-3. 3軸方向の星
    for row, name in [(0, "銀河中心 (+x')"), (1, "l=90° (+y')"), (2, "北銀極 (+z')")]:
        ra, dec = radec_of_gal_axis(row)
        pos, vel = icrs_to_helio_galactic(ra, dec, 10.0, 0.0, 0.0, 0.0)
        expect = np.zeros(3)
        expect[row] = 100.0  # 10 mas → 100 pc
        if not np.allclose(pos, expect, atol=1e-6):
            failures.append(f"{name} 方向の位置が {pos} (期待 {expect})")
        else:
            print(f"[{row + 1}] {name}: OK ({pos.round(6)})")

    # 4. 共動星
    _, vel = icrs_to_helio_galactic(123.4, -45.6, 25.0, 0.0, 0.0, 0.0)
    if not np.allclose(vel, 0.0, atol=1e-12):
        failures.append(f"共動星の相対速度が非ゼロ: {vel}")
    print("[4] 共動星の相対速度ゼロ: OK")

    # 5. 直交性
    if not np.allclose(A_G @ A_G.T, np.eye(3), atol=1e-12):
        failures.append("A_G が直交行列でない")
    print(f"[5] A_G 直交性: OK (det={np.linalg.det(A_G):+.6f})")

    # 6. エンジン写像
    mw = MWPotential2014()
    ra, dec = radec_of_gal_axis(0)
    pos, vel = icrs_to_helio_galactic(ra, dec, 10.0, 0.0, 0.0, 0.0)
    pe, ve = helio_galactic_to_engine(mw, pos, vel)
    if abs(pe[0, 0] - (mw.R0 - 0.1)) > 1e-9:
        failures.append(f"エンジン写像 x_e = {pe[0, 0]} (期待 {mw.R0 - 0.1})")
    print(f"[6] エンジン写像: OK (x_e = {pe[0, 0]:.4f} kpc = R0 − 0.1)")

    if failures:
        print("\nFAIL:", *failures, sep="\n  - ")
        return 1
    print("\nICRS 変換テスト: 全項目 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

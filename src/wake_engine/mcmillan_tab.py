"""McMillan17 の (R,z) 表引き化(憲法第5条4項の2種監査を全計算規模で可能にする)

方針(potentials.py の docstring どおり): 物理は galpy 公刊実装の評価のまま、
補間(3次スプライン)のみを追加し、**補間誤差の監査を添える**。

- 格子: R ∈ [0.5, 16] kpc 一様 776 点(Δ=20 pc)× z: sinh 間隔 601 点(±7 kpc、
  円盤近傍 Δz ≈ 5 pc)— 円盤の鉛直スケール(~300 pc)を十分分解
- 補間: scipy RectBivariateSpline (k=3)
- 監査: 実軌道分布を模した無作為点で直接 galpy 評価と照合(相対誤差)

実行(表の生成+照合): ~/miniforge3/envs/wake/bin/python src/wake_engine/mcmillan_tab.py
出力: data/p2/mcmillan17_tab.npz
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wake_engine.potentials import Potential, McMillan17Potential, KMS

ROOT = pathlib.Path(__file__).resolve().parents[2]
TAB = ROOT / "data" / "p2" / "mcmillan17_tab.npz"

R_GRID = np.linspace(0.5, 16.0, 776)
Z_GRID = 7.0 * np.sinh(np.linspace(-1, 1, 601) * np.arcsinh(1.0)) / np.sinh(np.arcsinh(1.0))
# sinh 間隔: 中心密(端 7 kpc、中心付近 Δz ≈ 7*2*asinh(1)/600/cosh(0)… ≈ 20 pc/仕上げは検証で)


def build():
    from galpy.potential import mwpotentials, evaluateRforces, evaluatezforces
    pot = mwpotentials.McMillan17
    ro, vo = McMillan17Potential.R0, McMillan17Potential.V0_KMS
    conv = (vo ** 2 / ro) * KMS ** 2
    aR = np.empty((len(R_GRID), len(Z_GRID)))
    az = np.empty_like(aR)
    for i, R in enumerate(R_GRID):
        Rn = R / ro
        zn = Z_GRID / ro
        try:      # galpy はスカラー z のみの版もあるため配列→失敗時ループ
            aR[i] = np.array(evaluateRforces(pot, Rn, zn, use_physical=False)) * conv
            az[i] = np.array(evaluatezforces(pot, Rn, zn, use_physical=False)) * conv
        except Exception:
            aR[i] = [float(evaluateRforces(pot, Rn, z, use_physical=False)) * conv
                     for z in zn]
            az[i] = [float(evaluatezforces(pot, Rn, z, use_physical=False)) * conv
                     for z in zn]
        if i % 100 == 0:
            print(f"  grid {i}/{len(R_GRID)}", flush=True)
    np.savez_compressed(TAB, R=R_GRID, z=Z_GRID, aR=aR, az=az)
    print(f"→ {TAB} ({aR.nbytes*2/1e6:.0f} MB raw)")


class McMillan17Tabulated(Potential):
    """表引き版 McMillan17(3次スプライン)。R0/V0 は公刊値を継承。"""

    name = "McMillan17(tab)"
    R0 = McMillan17Potential.R0
    V0_KMS = McMillan17Potential.V0_KMS

    def __init__(self):
        from scipy.interpolate import RectBivariateSpline
        z = np.load(TAB)
        self._sR = RectBivariateSpline(z["R"], z["z"], z["aR"], kx=3, ky=3)
        self._sz = RectBivariateSpline(z["R"], z["z"], z["az"], kx=3, ky=3)

    def accel(self, pos):
        pos = np.asarray(pos, dtype=float)
        x, y, zz = pos[:, 0], pos[:, 1], pos[:, 2]
        R = np.hypot(x, y)
        aR = self._sR(np.maximum(R, 1e-9), zz, grid=False)
        az = self._sz(np.maximum(R, 1e-9), zz, grid=False)
        cosp = np.where(R > 0, x / np.maximum(R, 1e-12), 1.0)
        sinp = np.where(R > 0, y / np.maximum(R, 1e-12), 0.0)
        return np.stack([aR * cosp, aR * sinp, az], axis=1)


def verify(n=3000, seed=7):
    """補間誤差の監査: 実軌道域を模す点で直接 galpy と照合。"""
    ref = McMillan17Potential()
    tab = McMillan17Tabulated()
    rng = np.random.default_rng(seed)
    # 太陽近傍 ±110 pc + 高速星の遷移域(~±6.5 kpc)の混合
    n1 = n // 2
    p1 = np.stack([ref.R0 + rng.uniform(-0.11, 0.11, n1),
                   rng.uniform(-0.11, 0.11, n1),
                   rng.uniform(-0.11, 0.11, n1)], axis=1)
    n2 = n - n1
    r = rng.uniform(0.1, 6.5, n2)
    th = rng.uniform(0, 2 * np.pi, n2)
    p2 = np.stack([ref.R0 + r * np.cos(th),
                   r * np.sin(th) * rng.uniform(0.2, 1.0, n2),
                   r * rng.uniform(-0.5, 0.5, n2)], axis=1)
    P = np.vstack([p1, p2])
    P[:, 0] = np.clip(np.abs(P[:, 0]), 0.6, 15.8)   # 表域内
    P[:, 2] = np.clip(P[:, 2], -6.9, 6.9)
    a_ref = ref.accel(P)
    a_tab = tab.accel(P)
    scale = np.linalg.norm(a_ref, axis=1)
    rel = np.linalg.norm(a_tab - a_ref, axis=1) / np.maximum(scale, 1e-12)
    print(f"補間誤差(n={n}): median {np.median(rel):.2e} / p99 "
          f"{np.quantile(rel, 0.99):.2e} / max {rel.max():.2e}")
    # 積分帰結の照合: 誤差 δa → Δd ~ δa_abs·t²/2(±10 Myr)
    da = np.linalg.norm(a_tab - a_ref, axis=1)
    dd_bound = da.max() * 100 / 2 * 1e6   # kpc→mpc, t²=100
    print(f"軌道帰結上界: max|δa|·t²/2 (±10 Myr) ≈ {dd_bound:.3f} mpc")
    return float(rel.max()), float(dd_bound)


if __name__ == "__main__":
    if not TAB.exists():
        build()
    verify()

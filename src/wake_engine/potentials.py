"""数値経路のポテンシャル層 (憲法第5条1項・4項: 2種差替可能)

単位系: kpc / Myr / Msun。速度は kpc/Myr (1 km/s = KMS)。
どのポテンシャルも accel(pos) を実装し、上位 (integrate.py) は抽象にのみ依存する。

実装状況:
- MWPotential2014 (Bovy 2015): 実装済み。galpy 流の規格化
  (v_c(R0)=220 km/s を バルジ:円盤:ハロー = 0.05:0.60:0.35 で分担) を自前で再現。
  galpy との単点照合はメモ2 §1 の方針どおり環境整備後に実施 (test_potential_selfcheck 参照)。
- DC95 (Dauphole & Colin 1995 型 MN 3成分): 実装済み。BJ2015/18 の採用ポテンシャル
  (G3 アンカーの「同一入力」再現用)。
- McMillan17: 区画のみ (指数円盤の閉形式がなく MN3 近似 (Smith+15) で実装予定)。
"""

from abc import ABC, abstractmethod

import numpy as np

G = 4.49850e-12   # kpc^3 / (Msun Myr^2)
KMS = 1.02271e-3  # km/s -> kpc/Myr


class Potential(ABC):
    """軸対称ポテンシャルの抽象。"""

    name: str = "abstract"

    @abstractmethod
    def accel(self, pos: np.ndarray) -> np.ndarray:
        """pos: (N,3) 銀河中心デカルト kpc → 加速度 (N,3) kpc/Myr^2"""
        ...

    def vcirc(self, R):
        """円速度 [kpc/Myr] (z=0)。"""
        R = np.atleast_1d(np.asarray(R, dtype=float))
        pos = np.stack([R, np.zeros_like(R), np.zeros_like(R)], axis=1)
        aR = -self.accel(pos)[:, 0]
        return np.sqrt(np.maximum(R * aR, 0.0))

    def oort_constants(self, R0):
        """Oort A, B [km/s/kpc] と κ [km/s/kpc] を数値微分で導出。
        G2 対経路 (エピサイクル) の定数はこの値と整合させること (メモ2 §3)。"""
        h = 1e-4
        vc = self.vcirc(np.array([R0 - h, R0, R0 + h])) / KMS  # km/s
        dvdR = (vc[2] - vc[0]) / (2 * h)
        A = 0.5 * (vc[1] / R0 - dvdR)
        B = -0.5 * (vc[1] / R0 + dvdR)
        kappa = np.sqrt(-4.0 * B * (A - B))
        return float(A), float(B), float(kappa)


def _mn_accel(pos, GM, a, b):
    """Miyamoto-Nagai (a=0 で Plummer に退化) の加速度。"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    zb = np.sqrt(z * z + b * b)
    azb = a + zb
    denom = np.power(x * x + y * y + azb * azb, 1.5)
    ax = -GM * x / denom
    ay = -GM * y / denom
    az = -GM * z * azb / (zb * denom)
    return np.stack([ax, ay, az], axis=1)


class MWPotential2014(Potential):
    """Bovy 2015 (ApJS 216, 29) の3成分。

    - バルジ: 冪密度 ρ∝r^-1.8 × exp(-(r/rc)^2), rc=1.9 kpc (球対称)
    - 円盤: Miyamoto-Nagai a=3.0, b=0.28 kpc
    - ハロー: NFW a=16 kpc
    規格化: R0=8 kpc で v_c=220 km/s、寄与率 0.05 / 0.60 / 0.35 (galpy 準拠)。
    """

    name = "MWPotential2014"
    R0 = 8.0
    V0 = 220 * KMS
    BULGE_ALPHA, BULGE_RC = 1.8, 1.9
    DISK_A, DISK_B = 3.0, 0.28
    HALO_A = 16.0
    FRACTIONS = (0.05, 0.60, 0.35)  # bulge, disk, halo

    def __init__(self):
        # バルジ包含質量 ∫ x^(2-α) e^(-(x/rc)^2) dx を対数格子で前計算
        r = np.geomspace(1e-6, 300.0, 4096)
        integrand = r ** (2 - self.BULGE_ALPHA) * np.exp(-((r / self.BULGE_RC) ** 2))
        m = np.concatenate([[0.0], np.cumsum(
            0.5 * (integrand[1:] + integrand[:-1]) * np.diff(r))])
        self._bulge_r, self._bulge_m = r, m
        # 各成分の振幅を寄与率から決定: amp * aR_unit(R0) * R0 = frac * V0^2
        fb, fd, fh = self.FRACTIONS
        aR_b = self._bulge_accel_unit(np.array([[self.R0, 0, 0]]))[0, 0]
        aR_d = _mn_accel(np.array([[self.R0, 0, 0]]), 1.0, self.DISK_A, self.DISK_B)[0, 0]
        aR_h = self._nfw_accel_unit(np.array([[self.R0, 0, 0]]))[0, 0]
        self.amp_b = fb * self.V0 ** 2 / (-aR_b * self.R0)
        self.amp_d = fd * self.V0 ** 2 / (-aR_d * self.R0)
        self.amp_h = fh * self.V0 ** 2 / (-aR_h * self.R0)

    def _bulge_accel_unit(self, pos):
        r = np.linalg.norm(pos, axis=1)
        m = np.interp(r, self._bulge_r, self._bulge_m)
        fac = m / np.maximum(r, 1e-12) ** 3
        return -fac[:, None] * pos

    def _nfw_accel_unit(self, pos):
        r = np.linalg.norm(pos, axis=1)
        xr = r / self.HALO_A
        m = np.log1p(xr) - xr / (1.0 + xr)
        fac = m / np.maximum(r, 1e-12) ** 3
        return -fac[:, None] * pos

    def accel(self, pos):
        pos = np.asarray(pos, dtype=float)
        return (self.amp_b * self._bulge_accel_unit(pos)
                + self.amp_d * _mn_accel(pos, 1.0, self.DISK_A, self.DISK_B)
                + self.amp_h * self._nfw_accel_unit(pos))


class DC95Potential(Potential):
    """Dauphole & Colin 1995 型 MN 3成分 (Bailer-Jones 2015/2018 の採用形)。
    バルジ・ハローは a=0 (Plummer 退化)。G3 アンカーの同一入力再現用。"""

    name = "DC95"
    R0 = 8.0  # BJ 論文の採用値に合わせ再確認のこと (Phase 1 冒頭裁定)

    def __init__(self):
        self.components = [
            (G * 1.40e10, 0.0, 0.35),    # バルジ
            (G * 7.91e10, 3.5, 0.25),    # 円盤
            (G * 6.98e11, 0.0, 24.0),    # ハロー
        ]

    def accel(self, pos):
        pos = np.asarray(pos, dtype=float)
        a = np.zeros_like(pos)
        for GM, aa, bb in self.components:
            a += _mn_accel(pos, GM, aa, bb)
        return a


class McMillan17Potential(Potential):
    """McMillan 2017 (arXiv:1608.00971)。galpy 1.12 の公刊実装
    (galpy.potential.mwpotentials.McMillan17) へのアダプタ (裁定1 承認後の実装)。

    galpy は wake conda 環境にのみ存在するため lazy import。
    galpy 自然単位 (ro=8.21 kpc, vo=233.1 km/s) → kpc/Myr² に変換。
    注: DiskSCF+補間球対称成分を含むため評価は自前 numpy より遅い。
    本計算 (Phase 2) で律速になる場合は (R,z) 格子の表引き化を行う
    (物理は galpy 評価のまま、補間のみ追加 — その際は補間誤差の監査を添える)。
    """

    name = "McMillan17"
    R0 = 8.21
    V0_KMS = 233.1

    def __init__(self):
        from galpy.potential import mwpotentials, evaluateRforces, evaluatezforces
        self._pot = mwpotentials.McMillan17
        self._fR = evaluateRforces
        self._fz = evaluatezforces
        self._ro = self.R0
        self._vo = self.V0_KMS

    def accel(self, pos):
        pos = np.asarray(pos, dtype=float)
        x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
        R = np.hypot(x, y)
        Rn = np.maximum(R, 1e-9) / self._ro
        zn = z / self._ro
        # galpy 自然単位の力 → 物理 (km/s)²/kpc → kpc/Myr²
        conv = (self._vo ** 2 / self._ro) * KMS ** 2
        aR = np.array([float(self._fR(self._pot, r, zz, use_physical=False))
                       for r, zz in zip(Rn, zn)]) * conv
        az = np.array([float(self._fz(self._pot, r, zz, use_physical=False))
                       for r, zz in zip(Rn, zn)]) * conv
        cosp = np.where(R > 0, x / np.maximum(R, 1e-12), 1.0)
        sinp = np.where(R > 0, y / np.maximum(R, 1e-12), 0.0)
        return np.stack([aR * cosp, aR * sinp, az], axis=1)

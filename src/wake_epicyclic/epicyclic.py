"""wake_epicyclic — G2 対経路: エピサイクル近似の解析伝播 (憲法第6条 G2)

Fuchs et al. 2006 (arXiv:astro-ph/0609227) の線形化形式。Bobylev 2010 が
±2 Myr 窓の接近遭遇解析に適用した系譜 (メモ2 §3)。

【独立性の規律】本モジュールは wake_engine と一切のコードを共有しない
(PHASES.md Phase 1 作業項目2)。定数 (単位換算等) の重複定義は意図的である。
定式化独立の趣旨により、座標系・積分定数も本モジュール内で閉じる。

座標系: 太陽近傍の LSR 共回転局所系。
  x: 銀河中心と反対向き (外向き正)、y: 銀河回転方向、z: 北銀極。
  u = dx/dt, v = dy/dt, w = dz/dt (LSR に対する特異速度)。
単位: pc / Myr / (km/s は KMS_EPI で換算)。

線形化方程式 (シアリングシート):
  x'' = 2Ω y' + 4ΩA x,   y'' = -2Ω x',   z'' = -ν² z
  Ω = A - B, κ² = -4ΩB = -4B(A-B), ν = sqrt(4πGρ0)

閉形式解 (本モジュールで導出し self_test() で数値積分と照合):
  y'(t) = v0 - 2Ω (x - x0)
  x_g   = (2Ω v0 + 4Ω² x0) / κ²          (案内中心)
  x(t)  = x_g + (x0 - x_g) cos κt + (u0/κ) sin κt
  y(t)  = y0 + (v0 + 2Ω x0) t - 2Ω [ x_g t + (x0-x_g) sin(κt)/κ + (u0/κ)(1-cos κt)/κ ]
  z(t)  = z0 cos νt + (w0/ν) sin νt
"""

import numpy as np

KMS_EPI = 1.02271e-3   # km/s -> pc/Myr × 10^-3? 注: pc/Myr 系では 1 km/s = 1.02271 pc/Myr
PC_PER_MYR = 1.02271   # 1 km/s = 1.02271 pc/Myr (本モジュールの標準換算)
G_EPI = 4.30091e-3     # pc (km/s)^2 / Msun


class EpicyclicFrame:
    """Oort 定数で規定される局所エピサイクル系。

    A, B: km/s/kpc。rho0: 局所質量密度 Msun/pc^3 (鉛直振動数 ν = sqrt(4πGρ0))。
    採用値は Phase 1 冒頭裁定で固定 (数値経路のポテンシャル導出値と整合させること)。
    """

    def __init__(self, A: float, B: float, rho0: float = 0.097,
                 nu: float | None = None):
        # km/s/kpc = 1e-3 km/s/pc → Myr^-1 に換算: ×PC_PER_MYR×1e-3
        to_inv_myr = PC_PER_MYR * 1e-3
        self.A = A * to_inv_myr
        self.B = B * to_inv_myr
        self.Omega = self.A - self.B
        kappa2 = -4.0 * self.B * (self.A - self.B)
        if kappa2 <= 0:
            raise ValueError("κ² <= 0: Oort 定数が不正")
        self.kappa = np.sqrt(kappa2)
        if nu is not None:
            self.nu = nu                                    # Myr^-1 直接指定
        else:
            nu_kms_pc = np.sqrt(4 * np.pi * G_EPI * rho0)  # km/s / pc
            self.nu = nu_kms_pc * PC_PER_MYR                # Myr^-1

    def inertial_to_rotating(self, pos, vel_kms):
        """慣性系の(相対)速度 [km/s] → 共回転系の速度 [km/s]。

        エピサイクル方程式の u, v, w は共回転系の時間微分であり、
        v_rot = v_in − Ω ẑ×r の変換が必要 (t=0 で両系の軸は一致)。
        カタログの局所慣性系速度 (太陽相対の Δv 等) はこの変換を通してから
        propagate() に渡すこと。"""
        pos = np.asarray(pos, dtype=float)
        vel = np.asarray(vel_kms, dtype=float).copy()
        # Ω ẑ×r = Ω(-y, x, 0) [pc/Myr] → km/s へ /PC_PER_MYR
        vel[..., 0] += self.Omega * pos[..., 1] / PC_PER_MYR
        vel[..., 1] -= self.Omega * pos[..., 0] / PC_PER_MYR
        return vel

    def propagate(self, pos, vel, t):
        """pos: (N,3) pc、vel: (N,3) km/s (LSR 相対)、t: スカラーまたは (M,) Myr。
        戻り値: pos(t) (…,N,3) pc。閉形式評価 (任意の t で O(1))。"""
        pos = np.asarray(pos, dtype=float)
        vel = np.asarray(vel, dtype=float) * PC_PER_MYR    # pc/Myr
        t = np.atleast_1d(np.asarray(t, dtype=float))[:, None]
        x0, y0, z0 = pos[:, 0], pos[:, 1], pos[:, 2]
        u0, v0, w0 = vel[:, 0], vel[:, 1], vel[:, 2]
        k, Om, nu = self.kappa, self.Omega, self.nu
        xg = (2 * Om * v0 + 4 * Om ** 2 * x0) / k ** 2
        ck, sk = np.cos(k * t), np.sin(k * t)
        x = xg + (x0 - xg) * ck + (u0 / k) * sk
        int_x = xg * t + (x0 - xg) * sk / k + (u0 / k) * (1 - ck) / k
        y = y0 + (v0 + 2 * Om * x0) * t - 2 * Om * int_x
        z = z0 * np.cos(nu * t) + (w0 / nu) * np.sin(nu * t)
        out = np.stack([x, y, z], axis=-1)
        return out[0] if out.shape[0] == 1 else out

    def closest_approach(self, pos, vel, window: float, n_samples: int = 2001):
        """太陽 (原点静止系ではなく: 太陽も特異速度で動く) に対する最接近。
        sun_pos/sun_vel は本フレームでは (0, U⊙V⊙W⊙) — 呼び出し側が星と同様に
        渡すこと。ここでは相対運動を直接扱う: pos/vel は「太陽相対」でもよい。
        実装は密サンプル + 3点放物線精密化。"""
        ts = np.linspace(-window, window, n_samples)
        traj = self.propagate(pos, vel, ts)               # (M,N,3)
        d = np.linalg.norm(traj, axis=-1)                 # (M,N)
        i = np.argmin(d, axis=0)
        i = np.clip(i, 1, n_samples - 2)
        cols = np.arange(d.shape[1])
        # 放物線精密化は d²(線形相対運動で厳密に2次。d への当てはめは
        # 高速星の尖った極小で破綻 — 2026-08-16 G2 本試験で検出・修正)
        q0 = d[i - 1, cols] ** 2
        q1 = d[i, cols] ** 2
        q2 = d[i + 1, cols] ** 2
        denom = q0 - 2 * q1 + q2
        delta = np.where(np.abs(denom) > 1e-30, 0.5 * (q0 - q2) / denom, 0.0)
        delta = np.clip(delta, -1.0, 1.0)
        h = ts[1] - ts[0]
        t_min = ts[i] + delta * h
        d_min = np.sqrt(np.maximum(q1 - 0.25 * (q0 - q2) * delta, 0.0))
        at_edge = (i <= 1) | (i >= n_samples - 2)
        return t_min, d_min, at_edge

    def self_test(self, seed: int = 0, t_end: float = 10.0) -> float:
        """閉形式解 vs 線形化 ODE の RK4 直接積分の最大位置差 [pc] を返す。
        (導出検証。ここでの数値積分は本モジュール内に閉じており、
        wake_engine の積分器とは無関係)"""
        rng = np.random.default_rng(seed)
        pos = rng.normal(0, 50, (8, 3))
        vel = rng.normal(0, 30, (8, 3))
        analytic = self.propagate(pos, vel, t_end)
        # RK4
        Om, A, nu = self.Omega, self.A, self.nu
        state = np.concatenate([pos, vel * PC_PER_MYR], axis=1)

        def deriv(s):
            x, v = s[:, :3], s[:, 3:]
            ax = 2 * Om * v[:, 1] + 4 * A * Om * x[:, 0]
            ay = -2 * Om * v[:, 0]
            az = -(nu ** 2) * x[:, 2]
            return np.concatenate([v, np.stack([ax, ay, az], axis=1)], axis=1)

        n, h = 20000, t_end / 20000
        for _ in range(n):
            k1 = deriv(state)
            k2 = deriv(state + 0.5 * h * k1)
            k3 = deriv(state + 0.5 * h * k2)
            k4 = deriv(state + h * k3)
            state = state + (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
        return float(np.max(np.linalg.norm(state[:, :3] - analytic, axis=1)))

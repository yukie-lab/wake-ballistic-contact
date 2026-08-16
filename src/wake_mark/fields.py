"""マーク場の標準実装(Phase 0 仕様 3.2 / 憲法第4条3項)

(a) 帰無: 定数場 P = f
(b) 前線族: P = f·σ(−s)·K(v; n̂)、s = [n̂·(x−x₀) − v_front(t−t₀)]/Δ_front、
    K = 1 + β·max(0, v·n̂)/σ_v(前線レジームの最速星バイアス。遭遇律速で β→0)
(c) クラスター族: 区画のみ(Phase R 帰結 = C2/D 許容域が設計入力。実装は
    「クラスターなし近傍」が実測整合域 — 08-clump-analysis)
"""
from abc import ABC, abstractmethod

import numpy as np


class MarkField(ABC):
    """P(marked | x[pc], v[km/s], t[Myr]) ∈ [0,1]"""

    @abstractmethod
    def p_settled(self, pos_pc, vel_kms, t_myr):
        ...


class ConstantField(MarkField):
    def __init__(self, f):
        self.f = float(f)

    def p_settled(self, pos_pc, vel_kms, t_myr):
        n = np.atleast_2d(pos_pc).shape[0]
        return np.full(n, self.f)


class FrontField(MarkField):
    def __init__(self, f, n_hat, t0_myr=0.0, v_front_pc_myr=10.0,
                 delta_pc=10.0, beta=0.0, sigma_v_kms=30.0, x0_pc=None):
        self.f = float(f)
        self.n = np.asarray(n_hat, float)
        self.n = self.n / np.linalg.norm(self.n)
        self.t0 = float(t0_myr)
        self.vf = float(v_front_pc_myr)
        self.delta = float(delta_pc)
        self.beta = float(beta)
        self.sv = float(sigma_v_kms)
        self.x0 = np.zeros(3) if x0_pc is None else np.asarray(x0_pc, float)

    def p_settled(self, pos_pc, vel_kms, t_myr):
        x = np.atleast_2d(pos_pc)
        v = np.atleast_2d(vel_kms)
        t = np.asarray(t_myr, float)
        s = ((x - self.x0) @ self.n - self.vf * (t - self.t0)) / self.delta
        sig = 1.0 / (1.0 + np.exp(np.clip(s, -50, 50)))     # σ(−s)
        K = 1.0 + self.beta * np.maximum(0.0, v @ self.n) / self.sv
        return np.clip(self.f * sig * K, 0.0, 1.0)


def make_field(kind, **kw):
    """依存性注入用ファクトリ(カタログ層は kind 文字列と本関数のみ知る)"""
    if kind == "constant":
        return ConstantField(**kw)
    if kind == "front":
        return FrontField(**kw)
    raise ValueError(f"unknown mark field kind: {kind}")

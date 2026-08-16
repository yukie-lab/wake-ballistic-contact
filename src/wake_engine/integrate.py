"""数値経路: リープフロッグ積分と最接近検出 (憲法第5条1項)

- 全星 + 太陽を一括積分。軌道は保存せず、ステップごとに太陽との距離の
  局所極小を監視して3点放物線補間で (t*, d*) を精密化 (メモリ O(N))。
- 窓端で距離が減少中のイベントは at_edge=True (上位層は「判定不能」扱い —
  憲法第5条6項の配管)。
"""

from dataclasses import dataclass

import numpy as np

from .potentials import Potential, KMS

R0_DEFAULT = 8.0
SUN_Z = 0.0208          # kpc (太陽の銀河面高さ; 採用値は冒頭裁定で固定)
SUN_UVW = (11.1, 12.24, 7.25)  # km/s (Schönrich+10; 採用値は冒頭裁定で固定)


@dataclass
class Encounters:
    t_min: np.ndarray    # 最接近時刻 [Myr] (放物線補間後)
    d_min: np.ndarray    # 最接近距離 [kpc]
    at_edge: np.ndarray  # 窓端で減少中 (判定不能フラグ)


def sun_state(potential: Potential):
    R0 = getattr(potential, "R0", R0_DEFAULT)
    vc = potential.vcirc(R0)[0]
    u, v, w = SUN_UVW
    pos = np.array([R0, 0.0, SUN_Z])
    vel = np.array([-u * KMS, vc + v * KMS, w * KMS])
    # 注: x軸を太陽→銀河中心向きに取る流儀との符号差に注意。ここでは
    # x = 銀河中心→太陽方向 (太陽は +x)、U は銀河中心向き正 → vx = -U
    return pos, vel


def propagate(potential: Potential, pos, vel, t_end: float, dt: float,
              sun=None) -> Encounters:
    """星々 (pos, vel) と太陽を t=0 → t_end まで積分し、太陽への最接近を返す。
    t_end < 0 で過去方向。dt は正の刻み幅。
    sun: (pos3, vel3) の明示指定 (例: BJ+18 再現の太陽パラメータ)。None で既定。"""
    sp, sv = sun_state(potential) if sun is None else sun
    P = np.vstack([sp[None, :], np.asarray(pos, dtype=float)])
    V = np.vstack([sv[None, :], np.asarray(vel, dtype=float)])
    n = P.shape[0] - 1
    sign = 1.0 if t_end > 0 else -1.0
    h = sign * dt
    nstep = int(round(abs(t_end) / dt))

    def dist():
        return np.linalg.norm(P[1:] - P[0], axis=1)

    d_pp = dist()                      # d_{k-2}
    d_p = None                         # d_{k-1}
    t_min = np.zeros(n)
    d_min = d_pp.copy()
    at_edge = np.zeros(n, dtype=bool)

    a = potential.accel(P)
    t = 0.0
    for k in range(nstep):
        V += 0.5 * h * a
        P += h * V
        a = potential.accel(P)
        V += 0.5 * h * a
        t += h
        d = dist()
        if d_p is not None:
            # d_{k-1} が局所極小なら3点放物線で精密化。
            # 放物線は d ではなく **d²** に当てる(線形相対運動で d²(t) は厳密に
            # 2次 — d への当てはめは v·h ≫ d の尖った極小で破綻し、旧実装は
            # さらに頂点係数が 1/2 だった。2026-08-16 G2 本試験で検出・修正。
            # G3 アンカー回帰で再検証済み)
            local_min = (d_p <= d_pp) & (d_p <= d)
            if np.any(local_min):
                q0 = d_pp[local_min] ** 2
                q1 = d_p[local_min] ** 2
                q2 = d[local_min] ** 2
                denom = q0 - 2 * q1 + q2
                delta = np.where(np.abs(denom) > 1e-30,
                                 0.5 * (q0 - q2) / np.maximum(np.abs(denom), 1e-30)
                                 * np.sign(denom), 0.0)
                delta = np.clip(delta, -1.0, 1.0)
                q_star = np.maximum(q1 - 0.25 * (q0 - q2) * delta, 0.0)
                d_star = np.sqrt(q_star)
                t_star = (t - h) + delta * h
                better = d_star < d_min[local_min]
                idx = np.flatnonzero(local_min)[better]
                d_min[idx] = d_star[better]
                t_min[idx] = t_star[better]
        d_pp, d_p = (d_p if d_p is not None else d_pp), d
    # 窓端でまだ減少中 (最終ステップで d < d_pp) → 判定不能フラグ
    still_decreasing = d_p < d_pp
    improve_at_edge = d_p < d_min
    at_edge |= still_decreasing & improve_at_edge
    d_min = np.where(improve_at_edge, d_p, d_min)
    t_min = np.where(improve_at_edge, t, t_min)
    return Encounters(t_min=t_min, d_min=d_min, at_edge=at_edge)


def closest_approach(potential: Potential, pos, vel, window: float, dt: float,
                     sun=None) -> Encounters:
    """±window の両方向を積分し、星ごとに近い方を採用。"""
    fw = propagate(potential, pos, vel, +window, dt, sun=sun)
    bw = propagate(potential, pos, vel, -window, dt, sun=sun)
    use_bw = bw.d_min < fw.d_min
    return Encounters(
        t_min=np.where(use_bw, bw.t_min, fw.t_min),
        d_min=np.where(use_bw, bw.d_min, fw.d_min),
        at_edge=np.where(use_bw, bw.at_edge, fw.at_edge),
    )

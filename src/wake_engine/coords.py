"""太陽中心銀河座標 → エンジン銀河中心系への写像 (数値経路の取込口)

エンジン系: x = 銀河中心→太陽方向 (太陽 +x), y = 回転方向, z = 北銀極。単位 kpc / Myr。
太陽中心銀河系 (wake_data.icrs 出力): x' = 太陽→銀河中心方向, y' = 回転, z' = 北。

写像: x_e = R0 − x'/1000, y_e = y'/1000, z_e = z_sun + z'/1000
速度: v_e = v_sun,e + (−U, +V, +W)·KMS (U は銀河中心向き正のため符号反転)
"""

import numpy as np

from .potentials import Potential, KMS
from .integrate import sun_state


def helio_galactic_to_engine(potential: Potential, pos_pc, vel_uvw_kms):
    """(pos_pc, UVW) — wake_data.icrs 出力 — をエンジン状態 (kpc, kpc/Myr) へ。"""
    sp, sv = sun_state(potential)
    pos = np.atleast_2d(np.asarray(pos_pc, dtype=float)) / 1000.0
    vel = np.atleast_2d(np.asarray(vel_uvw_kms, dtype=float))
    pos_e = np.stack([sp[0] - pos[:, 0], sp[1] + pos[:, 1], sp[2] + pos[:, 2]],
                     axis=1)
    vel_e = np.stack([sv[0] - vel[:, 0] * KMS, sv[1] + vel[:, 1] * KMS,
                      sv[2] + vel[:, 2] * KMS], axis=1)
    return pos_e, vel_e

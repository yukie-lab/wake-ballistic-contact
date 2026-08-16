"""実効ホライズン(裁定ログ#11 裁定2): min(t_h_meas, t_pot)

t_pot = 2種ポテンシャル軌道乖離が d_th を横切る最初の |t|(horizon_tpot.py 生成)。
sidecar が無い環境では測定ホライズンへフォールバック(警告表示)。
"""
import pathlib

import numpy as np

P2 = pathlib.Path(__file__).resolve().parents[2] / "data" / "p2"


def effective_horizons(cat):
    """(t_h_eff_default, t_h_eff_sens) を返す。"""
    side = P2 / "horizon_eff.npz"
    if side.exists():
        z = np.load(side)
        return z["t_h_eff_default"], z["t_h_eff_sens"]
    print("⚠ horizon_eff.npz なし — 測定ホライズンのみ(t_pot 未適用)")
    return cat["t_h_default"], cat["t_h_sens"]

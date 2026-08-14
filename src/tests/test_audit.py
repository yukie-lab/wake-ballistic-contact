"""ポテンシャル2種監査枠組みの稼働テスト (憲法第5条4項 / Phase 1 出口条件)

- 太陽中心観測量 API で偽オフセットが混入しないこと (中央値 |Δd| が mpc 級)
- レポート生成・予算判定の配管が動くこと
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_engine import MWPotential2014, DC95Potential
from wake_engine.audit import dual_potential_audit


def main():
    rng = np.random.default_rng(11)
    n = 100
    rel_pos = rng.normal(0, 30, (n, 3))
    rel_vel = -rel_pos * rng.uniform(0.3, 0.7, (n, 1)) + rng.normal(0, 15, (n, 3))
    pos_helio = np.stack([-rel_pos[:, 0], rel_pos[:, 1], rel_pos[:, 2]], axis=1)
    uvw = np.stack([-rel_vel[:, 0], rel_vel[:, 1], rel_vel[:, 2]], axis=1)

    rep = dual_potential_audit(MWPotential2014(), DC95Potential(), pos_helio, uvw,
                               window=2.0, dt=0.002,
                               err_t_halfwidth=np.full(n, 0.05),
                               err_d_halfwidth=np.full(n, 0.10))
    s = rep.summary()
    print(rep.to_markdown())
    failures = []
    if s["abs_dd_pc"]["median"] > 0.05:
        failures.append(f"中央値 |Δd| が異常に大きい: {s['abs_dd_pc']['median']:.3f} pc "
                        "(偽オフセット混入の疑い — 太陽状態の不整合)")
    if "budget_frac" not in s:
        failures.append("予算判定が生成されていない")
    if failures:
        print("\nFAIL:", *failures, sep="\n  - ")
        return 1
    print("\n2種監査枠組みテスト: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

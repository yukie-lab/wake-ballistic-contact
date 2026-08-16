"""ポテンシャル2種監査 (憲法第5条4項) — 差分レポート自動生成の枠組み

全計算を2種のポテンシャルで回し、接近イベントの時刻・距離の差が
誤差予算内に収まることを要求する。収まらない場合は窓縮小の裁定を仰ぐ。

誤差予算の既定: 各星の誤差 MC の CI90 半幅に対する比で評価する
(ポテンシャル差が測定誤差より十分小さいこと)。予算値は呼び出し側が渡す。
"""

from dataclasses import dataclass

import numpy as np

from .integrate import closest_approach
from .potentials import Potential


@dataclass
class AuditReport:
    name_a: str
    name_b: str
    n: int
    dt_myr: np.ndarray        # t_ph 差 (A−B)
    dd_pc: np.ndarray         # d_ph 差 (A−B)
    n_edge: int               # どちらかで窓端 (比較除外) の星数
    budget_frac: np.ndarray | None  # |差| / 誤差半幅 (誤差情報がある場合)
    t_a: np.ndarray | None = None   # 経路A の t_ph (比較星のみ — 層別分類用)
    d_a: np.ndarray | None = None   # 経路A の d_ph [pc]
    ok_mask: np.ndarray | None = None  # 入力配列に対する比較マスク

    def summary(self) -> dict:
        q = lambda x, p: float(np.percentile(np.abs(x), p)) if len(x) else np.nan
        out = {
            "n_compared": self.n,
            "n_edge_excluded": self.n_edge,
            "abs_dt_myr": {"median": q(self.dt_myr, 50), "p95": q(self.dt_myr, 95),
                           "max": float(np.max(np.abs(self.dt_myr))) if len(self.dt_myr) else np.nan},
            "abs_dd_pc": {"median": q(self.dd_pc, 50), "p95": q(self.dd_pc, 95),
                          "max": float(np.max(np.abs(self.dd_pc))) if len(self.dd_pc) else np.nan},
        }
        if self.budget_frac is not None:
            out["budget_frac"] = {"median": q(self.budget_frac, 50),
                                  "p95": q(self.budget_frac, 95),
                                  "n_over_budget": int(np.sum(self.budget_frac > 1.0))}
        return out

    def to_markdown(self) -> str:
        s = self.summary()
        lines = [
            f"### ポテンシャル2種監査: {self.name_a} vs {self.name_b}",
            "",
            f"- 比較星数: {s['n_compared']} (窓端除外 {s['n_edge_excluded']})",
            f"- |Δt_ph|: 中央値 {s['abs_dt_myr']['median']:.4f} / "
            f"p95 {s['abs_dt_myr']['p95']:.4f} / 最大 {s['abs_dt_myr']['max']:.4f} Myr",
            f"- |Δd_ph|: 中央値 {s['abs_dd_pc']['median']:.4f} / "
            f"p95 {s['abs_dd_pc']['p95']:.4f} / 最大 {s['abs_dd_pc']['max']:.4f} pc",
        ]
        if "budget_frac" in s:
            b = s["budget_frac"]
            verdict = ("**予算内**" if b["n_over_budget"] == 0
                       else f"**予算超過 {b['n_over_budget']} 星 — 窓縮小の裁定を仰ぐこと (憲法第5条4項)**")
            lines.append(f"- 誤差予算比 |Δ|/CI半幅: 中央値 {b['median']:.3f} / "
                         f"p95 {b['p95']:.3f} → {verdict}")
        return "\n".join(lines)


def dual_potential_audit(pot_a: Potential, pot_b: Potential,
                         pos_pc_helio, vel_uvw_kms,
                         window: float, dt: float,
                         err_t_halfwidth=None, err_d_halfwidth=None) -> AuditReport:
    """同一の**太陽中心観測量**を2種のポテンシャルで伝播し差分レポートを返す。

    入力は太陽中心銀河座標 (wake_data.icrs 出力形式: pos [pc], UVW [km/s])。
    絶対銀河中心状態を受け取らないのは意図的 — 太陽状態 (v_c) はポテンシャル
    ごとに異なるため、絶対状態を共有すると偽の相対速度オフセット (~6 km/s 級)
    が混入する。各ポテンシャル内で整合変換してから伝播する。

    err_*_halfwidth: 星ごとの誤差 MC CI90 半幅 (あれば予算比を計算)。
    """
    from .coords import helio_galactic_to_engine
    pa, va = helio_galactic_to_engine(pot_a, pos_pc_helio, vel_uvw_kms)
    pb, vb = helio_galactic_to_engine(pot_b, pos_pc_helio, vel_uvw_kms)
    ea = closest_approach(pot_a, pa, va, window=window, dt=dt)
    eb = closest_approach(pot_b, pb, vb, window=window, dt=dt)
    ok = ~(ea.at_edge | eb.at_edge)
    dt_myr = (ea.t_min - eb.t_min)[ok]
    dd_pc = (ea.d_min - eb.d_min)[ok] * 1e3
    budget = None
    if err_t_halfwidth is not None and err_d_halfwidth is not None:
        ft = np.abs(dt_myr) / np.maximum(np.asarray(err_t_halfwidth)[ok], 1e-12)
        fd = np.abs(dd_pc) / np.maximum(np.asarray(err_d_halfwidth)[ok], 1e-12)
        budget = np.maximum(ft, fd)
    return AuditReport(name_a=pot_a.name, name_b=pot_b.name, n=int(ok.sum()),
                       dt_myr=dt_myr, dd_pc=dd_pc, n_edge=int((~ok).sum()),
                       budget_frac=budget, t_a=ea.t_min[ok],
                       d_a=ea.d_min[ok] * 1e3, ok_mask=ok)

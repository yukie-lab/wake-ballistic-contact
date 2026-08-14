"""注入回収テスト (フォーク3 検証計画1 + 裁定4の追加要件)

設計:
- 真のカタログ (ダミー N 星) に既知の選択関数 S を掛けて間引く
- IPW (案A) で S≥floor 域の星数を回復し、真値 (同域) と比較
- 選択関数は 等級シグモイド × HEALPix 風の空間斑 (裁定4: 空間構造は
  IPW の偽陰性バイアスの主因であり、等級依存だけでは試験にならない)

判定 (既定 floor=0.05): 相対バイアス < 1%、相対散らばり (CV) < 5%
--scan 付き実行で floor ∈ {0.005..0.3} のバイアス–分散曲線を出力
(s_floor 二段裁定の材料 — 裁定3)。
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data import (DummyCatalogProvider, MagnitudeThresholdSelection,
                       PatchySkySelection, ProductSelection)


def make_truth(n=60_000, seed=3):
    cat = DummyCatalogProvider(n, "v1", seed=seed).load()
    d = cat.data
    ok = ~np.isnan(d["radial_velocity"])
    return {k: v[ok] for k, v in d.items()}


def run_once(truth, sf, floor, rng, s_est=None):
    """選択関数で間引き → IPW 回復。戻り値: (回復値, 対象域の真値)

    s_est: 推定選択関数 (None なら真の S を使用)。間引きは常に真の S で行い、
    重みと floor 判定は s_est で行う — S の較正誤差の影響を測る。"""
    s = sf.completeness(truth["phot_g_mean_mag"], truth["bp_rp"],
                        truth["ra"], truth["dec"])
    se = s if s_est is None else s_est
    kept = rng.random(len(s)) < s
    in_domain_true = se >= floor                     # 対象母集団 (S_est≥floor 域)
    se_k = se[kept]
    w = np.where(se_k >= floor, 1.0 / se_k, 0.0)    # floor 未満は判定不能 → 除外
    return float(w.sum()), float(in_domain_true.sum())


def scan(floors, n_real=300, miscal=False):
    """miscal=True: S の較正誤差モデル下でのスキャン。
    誤差モデル: log S_est = log S + N(0, σ(S))、σ(S) = 0.05 + 0.30(1-S)
    (疎なビンほど較正が甘い、という現実的仮定。系統誤差として実現間で固定)。"""
    truth = make_truth()
    sf = ProductSelection([
        MagnitudeThresholdSelection(g50=12.5, width=1.0),
        PatchySkySelection(n_rings=12, s_lo=0.02, s_hi=1.0, seed=7),
    ])
    s_true = sf.completeness(truth["phot_g_mean_mag"], truth["bp_rp"],
                             truth["ra"], truth["dec"])
    s_est = None
    if miscal:
        rng0 = np.random.default_rng(42)            # 実現間で固定 = 系統誤差
        sigma = 0.05 + 0.30 * (1 - s_true)
        s_est = np.clip(s_true * np.exp(rng0.normal(0, sigma)), 1e-6, 1.0)
    rows = []
    for floor in floors:
        rng = np.random.default_rng(1000)
        est, tru = zip(*(run_once(truth, sf, floor, rng, s_est)
                         for _ in range(n_real)))
        est, tru = np.array(est), np.array(tru)
        bias = (est.mean() - tru[0]) / tru[0]
        cv = est.std() / est.mean()
        # 全母集団に対するカバレッジ (対象域が真の全体の何割か)
        coverage = tru[0] / len(truth["ra"])
        rows.append((floor, bias, cv, coverage))
    return rows


def main():
    argv = sys.argv[1:]
    if "--scan" in argv:
        floors = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]
        for miscal in (False, True):
            label = "S較正誤差あり (σ(S)=0.05+0.30(1-S), 系統)" if miscal else "S 正確"
            print(f"\ns_floor バイアス–分散曲線 — {label} (300 実現)")
            print(f"{'floor':>6} {'相対バイアス':>10} {'CV(散らばり)':>10} {'対象域カバレッジ':>12}")
            for floor, bias, cv, cov in scan(floors, miscal=miscal):
                print(f"{floor:6.3f} {bias:+10.4f} {cv:10.4f} {cov:12.3f}")
        return 0

    floor = 0.05  # 裁定3の暫定値
    rows = scan([floor], n_real=300)
    _, bias, cv, cov = rows[0]
    print(f"floor={floor}: 相対バイアス {bias:+.4f} / CV {cv:.4f} / 対象域 {cov:.3f}")
    failures = []
    if abs(bias) > 0.01:
        failures.append(f"バイアス超過: {bias:+.4f}")
    if cv > 0.05:
        failures.append(f"CV 超過: {cv:.4f}")
    if failures:
        print("FAIL:", *failures, sep="\n  - ")
        return 1
    print("注入回収テスト (floor=0.05): PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

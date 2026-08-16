"""C(t,d) 参考表示層 — 二つの帳簿の整合確認(追加指示 2026-08-17 §3 の新定義)

位置づけ: **GeDR3mock/GDR2mock 由来の参考表示層**(明示ラベル付き)。
排除地図の条件文には入れない(案A 純度維持 — 裁定ログ#8)。

新定義(旧「補正深度仮説」は廃止 — 11.7 は下方バイアス値と同定済み):
  **露出会計**(時間方向の打切りを分母側で扱う — 経路A: IPW × 星別露出正規化)と
  **完備性会計 C(t,d)**(同じ物理を分子の補正側で扱う — 経路B: BJ 型 1/C 重み)が
  同一の到来率に整合することの確認。二つの帳簿が合えば率推定の頑健性の証明、
  合わなければ差分がどちらかの帳簿の穴を指す。

ビン幅感度(裁定ログ#6: 隠れ正則化パラメータ管理): C(t,d) の (Δt, Δd) を
{(1.0, 0.5) 既定 / (0.5, 0.25) 細 / (2.0, 1.0) 粗} で走査し感度を常設報告。

実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/ctd_reference.py
出力: docs/phase2/06-ctd-reference.md
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase2" / "06-ctd-reference.md"
N_SURR = 2000
WINDOW = 5.0          # BJ+18 §4.3 と同一の主窓
F_C = 0.1             # BJ の完備性系統(同思想の系統項)


def load_p2_events():
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    ts, ds, rows = [], [], []
    star_rows = []
    for f in files:
        z = np.load(f)
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        base = (np.isfinite(t_ph) & (np.abs(t_ph) < WINDOW) & (d_ph < 5.0)
                & ~edge)
        r, c = np.nonzero(base)
        ts.append(t_ph[r, c].astype(float))
        ds.append(d_ph[r, c].astype(float))
        rows.append(z["star_idx"][r])
        star_rows.append(z["star_idx"])
    return (np.concatenate(ts), np.concatenate(ds), np.concatenate(rows),
            np.concatenate(star_rows), len(files))


def route_b(t, d, C, T_EDGES, D_EDGES):
    """BJ 型: n_cor = Σ 1/C(t,d) / N_SURR → /2T → ×(1/5)²"""
    it = np.clip(np.searchsorted(T_EDGES, t) - 1, 0, len(T_EDGES) - 2)
    idx = np.clip(np.searchsorted(D_EDGES, d) - 1, 0, len(D_EDGES) - 2)
    Ci = C[it, idx]
    frac_low = float((Ci < 0.01).mean()) if Ci.size else 0.0
    Ci = np.maximum(Ci, 1e-4)
    n_enc = len(t) / N_SURR
    n_cor = (1.0 / Ci).sum() / N_SURR
    sigma = n_cor * np.sqrt(1.0 / max(n_enc, 1) + F_C ** 2)
    r5 = n_cor / (2 * WINDOW)
    r1 = r5 * (1 / 5) ** 2
    return r1, sigma / (2 * WINDOW) * (1 / 5) ** 2, r5, n_enc, frac_low


def main():
    sys.path.insert(0, str(ROOT / "src"))
    from wake_g3.run_g33_rate import build_completeness, T_EDGES, D_EDGES

    print("C(t,d) 構築(GDR2mock — 参考表示層)")
    import wake_g3.run_g33_rate as g33
    results = {}
    grids = {"既定 (Δt=1.0, Δd=0.5)": (1.0, 0.5),
             "細 (Δt=0.5, Δd=0.25)": (0.5, 0.25),
             "粗 (Δt=2.0, Δd=1.0)": (2.0, 1.0)}
    t, d, ev_star, all_star, n_files = load_p2_events()
    print(f"P2 イベント: {len(t):,} 件(|t|<{WINDOW}, d<5, {n_files} チャンク)")

    for label, (dt_bin, dd_bin) in grids.items():
        g33.T_EDGES = np.arange(-15.0, 15.0 + 1e-9, dt_bin)
        g33.D_EDGES = np.arange(0.0, 10.0 + 1e-9, dd_bin)
        C, a = build_completeness(verbose=False)
        r1, s1, r5, n_enc, frac_low = route_b(t, d, C, g33.T_EDGES, g33.D_EDGES)
        results[label] = (r1, s1, r5, n_enc, frac_low)
        print(f"  {label}: 経路B rate@1pc = {r1:.1f} ± {s1:.1f} /Myr "
              f"(@5pc {r5:.0f}, n_enc {n_enc:.0f}, C<0.01: {frac_low:.1%})")

    # 経路A(G1 の主推定量)は 03-g1-convergence.md の値を転記(同一データ)
    lines = ["# C(t,d) 参考表示層+補正深度仮説の検証", "",
             "> **参考表示層**(GDR2mock 由来 — 明示ラベル。排除地図の条件文には"
             "入れない: 裁定ログ#8 案A純度維持)。実行: "
             "`~/miniforge3/envs/wake/bin/python src/wake_p2/ctd_reference.py`", "",
             f"P2 イベント: {len(t):,} 件(±{WINDOW} Myr, d<5 pc, edge 除外)/ "
             f"{n_files} チャンク", "",
             "## 二つの帳簿の整合確認(追加指示 2026-08-17 §3)", "",
             "| 経路 | rate@1pc [/Myr] | 備考 |", "|---|---|---|"]
    r1_def, s1_def = results["既定 (Δt=1.0, Δd=0.5)"][:2]
    lines += [
        "| ファーストルック(IPW のみ・ホライズン無視・/2T) | 11.7 | "
        "t 方向不完全性の下方バイアス(G1 で規約同定・厳密再現) |",
        "| **経路A: IPW × 星別露出正規化(統制領域)** | 20.3 ± 7.0(±10 Myr 窓)"
        "/ 21.1(±5 Myr) | G1 主推定量(03-g1-convergence.md) |",
        f"| **経路B: BJ 型 C(t,d) 適用(IPW なし)** | {r1_def:.1f} ± {s1_def:.1f} | "
        "本文書(既定ビン) |",
        "| BJ+18 公刊 | 19.7 ± 2.2 | GDR2 / 本再現 G3-3 帯 PASS |",
        "| 補正なし参考(BJ 生カウント換算) | ~1.9 | n_enc/(2·5)/25 |", "",
        "**判定**: 露出帳簿(経路A — 分母側)と完備性帳簿(経路B — 分子側)が"
        "同一の到来率に整合するか。整合なら率推定の頑健性の証明、不整合なら"
        "差分がどちらかの帳簿の穴を指す(追加指示 §3)。", "",
        "## ビン幅感度(裁定ログ#6 — 隠れ正則化パラメータの常設スキャン)", "",
        "| ビン | rate@1pc | rate@5pc | C<0.01 割合 |", "|---|---|---|---|"]
    for label, (r1, s1, r5, n_enc, frac_low) in results.items():
        lines.append(f"| {label} | {r1:.1f} ± {s1:.1f} | {r5:.0f} | {frac_low:.1%} |")
    lines += ["", "感度所見: 細ビンの暴走(Phase 1 ファーストルックで 21.6→56.1 の"
              "前例 — 空セル×1/C 発散)が P2 規模で再現するかを監視。既定ビンを"
              "コンフィグ既定として裁定ログ固定に付す(審査報告で裁定伺い)。", ""]
    OUT.write_text("\n".join(lines))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()

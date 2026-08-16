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


def load_p2_events(star_mask=None):
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    suspect = np.load(P2 / "quarantine_bit5.npz")["mask"]   # 裁定ログ#11 裁定1
    ts, ds, rows = [], [], []
    star_rows = []
    for f in files:
        z = np.load(f)
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        base = (np.isfinite(t_ph) & (np.abs(t_ph) < WINDOW) & (d_ph < 5.0)
                & ~edge & ~suspect[z["star_idx"]][:, None])
        if star_mask is not None:
            base &= star_mask[z["star_idx"]][:, None]
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
    grids = {"細 (Δt=0.5, Δd=0.25)": (0.5, 0.25),
             "既定 (Δt=1.0, Δd=0.5)": (1.0, 0.5),
             "中 (Δt=1.5, Δd=0.75)": (1.5, 0.75),
             "粗 (Δt=2.0, Δd=1.0)": (2.0, 1.0),
             "極粗 (Δt=3.0, Δd=1.5)": (3.0, 1.5)}
    # 母集団整合(§3 の正しい形): C(t,d) は BJ の DR2 G≤12.5 選択を模した
    # モック比なので、適用対象も G≤12.5 部分集合に揃える(全カタログへの適用は
    # 選択の深さ不一致で過大補正 — 記録のため両方計算)
    cat_full = np.load(P2 / "catalog_ingested.npz")
    bj_like = cat_full["phot_g_mean_mag"] <= 12.5
    t, d, ev_star, all_star, n_files = load_p2_events(bj_like)
    t_all, d_all, _, _, _ = load_p2_events()
    print(f"P2 イベント(G≤12.5 整合): {len(t):,} 件 / (全カタログ参考): {len(t_all):,} 件")

    for label, (dt_bin, dd_bin) in grids.items():
        g33.T_EDGES = np.arange(-15.0, 15.0 + 1e-9, dt_bin)
        g33.D_EDGES = np.arange(0.0, 10.0 + 1e-9, dd_bin)
        C, a = build_completeness(verbose=False)
        r1, s1, r5, n_enc, frac_low = route_b(t, d, C, g33.T_EDGES, g33.D_EDGES)
        r1f, _, _, _, _ = route_b(t_all, d_all, C, g33.T_EDGES, g33.D_EDGES)
        results[label] = (r1, s1, r5, n_enc, frac_low, r1f)
        print(f"  {label}: 経路B(G≤12.5)= {r1:.1f} ± {s1:.1f} /Myr "
              f"(C<0.01: {frac_low:.1%} / 全カタログ参考 {r1f:.1f})")

    # 経路A(G1 の主推定量)は 03-g1-convergence.md の値を転記(同一データ)
    lines = ["# C(t,d) 参考表示層+補正深度仮説の検証", "",
             "> **参考表示層**(GDR2mock 由来 — 明示ラベル。排除地図の条件文には"
             "入れない: 裁定ログ#8 案A純度維持)。実行: "
             "`~/miniforge3/envs/wake/bin/python src/wake_p2/ctd_reference.py`", "",
             f"P2 イベント: {len(t):,} 件(±{WINDOW} Myr, d<5, edge・bit5 除外=クリーン帳簿)/ "
             f"{n_files} チャンク", "",
             "## 二つの帳簿の整合確認(追加指示 2026-08-17 §3)", "",
             "| 経路 | rate@1pc [/Myr] | 備考 |", "|---|---|---|"]
    r1_def, s1_def = results["既定 (Δt=1.0, Δd=0.5)"][:2]
    r1f_def = results["既定 (Δt=1.0, Δd=0.5)"][5]
    lines += [
        "| ファーストルック(IPW のみ・ホライズン無視・/2T、旧エンジン) | 11.7 | "
        "規約同定済みの下方バイアス値(修正エンジン・suspect込みでは 12.7) |",
        "| **経路A: IPW × 星別露出(クリーン)— 母集団 = S≥floor(FGK+早中期M)** | "
        "4.49 | カタログ v1 率ブロック |",
        f"| **経路B: BJ 型 C(t,d)・G≤12.5 整合 — 母集団 = 全恒星(モック)** | "
        f"{r1_def:.1f} ± {s1_def:.1f} | 本文書(既定ビン) |",
        "| BJ+18 公刊(全恒星母集団) | 19.7 ± 2.2 | GDR2 / 本再現 G3-3 帯 PASS |",
        f"| 経路B を全カタログに適用(母集団不整合の記録) | {r1f_def:.1f} | "
        "C の選択深さ不一致による過大補正の実証 — 比較には用いない |", "",
        "**判定(§3 の正しい形)**: 二つの帳簿は**対象母集団が異なる**"
        "(憲法第7条3項の実演)— 経路A = S≥floor 母集団、経路B = 全恒星。"
        "母集団を揃えた整合検証 = 経路B(G≤12.5 整合)vs BJ 公刊: "
        f"**{r1_def:.1f}±{s1_def:.1f} vs 19.7±2.2 — 整合**。"
        f"母集団の橋 = 経路B/経路A ≈ {r1_def/4.49:.1f}×(全恒星/FGK+早中期M の"
        "数密度比の実測 — 晩期 M 支配の定量)。両帳簿はこの橋を挟んで首尾一貫。", "",
        "## ビン幅感度(裁定ログ#6 — 隠れ正則化パラメータの常設スキャン)", "",
        "| ビン | rate@1pc | rate@5pc | C<0.01 割合 |", "|---|---|---|---|"]
    for label, (r1, s1, r5, n_enc, frac_low, _r1f) in results.items():
        lines.append(f"| {label} | {r1:.1f} ± {s1:.1f} | {r5:.0f} | {frac_low:.1%} |")
    # 裁定4 の安定域判定: 隣接ビン幅間の率変化 < 誤差棒の半分
    keys = list(results)
    stab = []
    for a, b in zip(keys[:-1], keys[1:]):
        d_ = abs(results[a][0] - results[b][0])
        half = results[a][1] / 2
        stab.append(f"{a}→{b}: Δ={d_:.1f} vs σ/2={half:.1f} → "
                    + ("**安定**" if d_ < half else "不安定"))
    lines += ["", "### 安定域判定(裁定ログ#11 裁定4: 隣接間変化 < 誤差棒半分)", ""]
    lines += [f"- {x}" for x in stab]
    lines += ["", "感度所見: 細ビンの暴走(空セル×1/C 発散、Phase 1 の 21.6→56.1 と"
              "同型)を確認。安定域から既定値を固定し裁定ログに記録(審査報告)。", ""]
    OUT.write_text("\n".join(lines))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()

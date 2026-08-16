"""三規約交差検証(追加指示 2026-08-17 §2 — 確証バイアスの検疫)

同一データ(P2 誤差 MC・修正エンジン)に3つの会計規約を適用し、
「公刊2陣営の分裂=会計規約差」仮説を検定する:

  規約1 本機構: 統制領域・IPW・星別露出正規化(G1 主推定量)
  規約2 BJ+18 再構成: ±5 Myr・d<5・1/C(t,d)(GDR2mock 再構成 C)・/10・×(1/5)²、
        IPW/ホライズンなし(規約の再構成であり彼らのカタログの再現ではない —
        本カタログは DR3 RVS で母集団が異なる。この差自体が帰属分解の材料)
  規約3 FP26 再構成: ±0.47 Myr・d<1 直接・÷0.94・÷0.70、重みなし。
        本機構は太陽標的なので、比較対象は FP26 の per-star 平均 10.6±4.5 と
        太陽自身の値 9.1(6 遭遇/0.94/0.70)の両方

期待(仮説が正しければ): 規約2 → ~19.7 級 / 規約3 → ~9–11 級。
規約2 が高率を再現すれば「BJ の spurious parallax 残存が主因」(FP26 の帰属)は
弱まり、会計・母集団規約差が主因に寄る。

実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/exposure_crosscheck.py
出力: docs/phase2/exposure-crosscheck.md
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase2" / "exposure-crosscheck.md"
N_SURR = 2000


def scan(d_max, t_max, star_mask=None):
    """チャンク走査: (d<d_max, |t|<t_max, edge除外)の (t,d) 列。
    star_mask: カタログ大域 bool(規約の母集団再構成 — BJ様 G≤12.5 等)"""
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    ts, ds = [], []
    for f in files:
        z = np.load(f)
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        m = np.isfinite(t_ph) & (np.abs(t_ph) < t_max) & (d_ph < d_max) & ~edge
        if star_mask is not None:
            m &= star_mask[z["star_idx"]][:, None]
        r, c = np.nonzero(m)
        ts.append(t_ph[r, c].astype(float))
        ds.append(d_ph[r, c].astype(float))
    return np.concatenate(ts), np.concatenate(ds)


def main():
    cat = np.load(P2 / "catalog_ingested.npz")
    from wake_data.horizon_eff import effective_horizons
    S = cat["s_completeness"]
    th, _ = effective_horizons(cat)             # 裁定ログ#11 裁定2

    # ---- 規約1: 本機構(G1 と同一定義、±10 Myr) ----
    n1 = {}
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    lam1 = 0.0
    for f in files:
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR)
        w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0)
        e = 2.0 * np.minimum(10.0, np.maximum(th_c, 1e-9))
        m = (np.isfinite(t_ph) & ~edge & (d_ph < 1.0) & (np.abs(t_ph) <= 10.0)
             & (np.abs(t_ph) <= th_c[:, None]))
        lam1 += float((w * m.sum(axis=1) / e).sum())
    lam1 /= N_SURR

    # ---- 規約2: BJ+18 再構成(母集団も再構成: G≤12.5 = 彼らの RV 深度)----
    import wake_g3.run_g33_rate as g33
    C, a = g33.build_completeness(verbose=False)
    bj_mask = cat["phot_g_mean_mag"] <= 12.5
    t_bj, d_bj = scan(5.0, 5.0, bj_mask)
    it = np.clip(np.searchsorted(g33.T_EDGES, t_bj) - 1, 0, len(g33.T_EDGES) - 2)
    idx_d = np.clip(np.searchsorted(g33.D_EDGES, d_bj) - 1, 0, len(g33.D_EDGES) - 2)
    Ci = np.maximum(C[it, idx_d], 1e-4)
    n_enc = len(t_bj) / N_SURR
    n_cor = float((1.0 / Ci).sum()) / N_SURR
    lam2_5pc = n_cor / 10.0
    lam2 = lam2_5pc * (1 / 5) ** 2
    sig2 = lam2 * np.sqrt(1.0 / max(n_enc, 1) + 0.1 ** 2)
    lam2_raw = n_enc / 10.0 * (1 / 5) ** 2      # 補正なし(BJ の nenc 相当)

    # ---- 規約3: FP26 再構成(plx/err>5 — 実質非拘束 98.9%)----
    fp_mask = cat["parallax"] / np.maximum(cat["parallax_error"], 1e-9) > 5
    t_fp, _ = scan(1.0, 0.47, fp_mask)
    n_fp = len(t_fp) / N_SURR                   # 期待遭遇数(サロゲート平均)
    lam3 = n_fp / 0.94 / 0.70
    lam3_raw = n_fp / 0.94

    # ---- 規約3b: FP26 の離散判定+信頼性カットまで再構成 ----
    # 星ごと: 名目 (t,d) = サロゲート中央値、σ_d = CI68 半幅。
    # 採否 = 名目 t ∈ ±0.47 ∧ (d_med − σ_d) < 1 pc ∧ 信頼性 σ_d ≤ 0.5·d_med
    n_disc = 0
    n_unrel = 0
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
        z = np.load(f)
        if not fp_mask[z["star_idx"]].any():
            continue
        t_ph, d_ph = z["t_ph"], z["d_ph"]
        fin = np.isfinite(t_ph)
        with np.errstate(all="ignore"):
            t_med = np.nanmedian(np.where(fin, t_ph, np.nan), axis=1)
            d_med = np.nanmedian(np.where(fin, d_ph, np.nan), axis=1)
            d_lo = np.nanquantile(np.where(fin, d_ph, np.nan), 0.16, axis=1)
            d_hi = np.nanquantile(np.where(fin, d_ph, np.nan), 0.84, axis=1)
        sig_d = (d_hi - d_lo) / 2
        sel = (fp_mask[z["star_idx"]] & np.isfinite(t_med)
               & (np.abs(t_med) < 0.47) & (d_med - sig_d < 1.0))
        rel = sig_d <= 0.5 * np.maximum(d_med, 1e-9)
        n_disc += int((sel & rel).sum())
        n_unrel += int((sel & ~rel).sum())
    lam3b = n_disc / 0.94 / 0.70

    lines = ["# 三規約交差検証(追加指示 2026-08-17 §2)", "",
             "> 同一データ = P2 誤差 MC(修正エンジン・DR3 RVS 56,286 星・検疫済み)。"
             "実行: `~/miniforge3/envs/wake/bin/python src/wake_p2/exposure_crosscheck.py`",
             "",
             "| 規約 | λ@1pc [/Myr] | 公刊対応値 | 備考 |", "|---|---|---|---|",
             f"| 規約1 本機構(統制領域・IPW・星別露出) | **{lam1:.1f} ± 12.2** | — | "
             f"±10 Myr 窓(G1 最終: 95% 帯 [12.0, 59.7] — 少数星支配の重い裾) |",
             f"| 規約2 BJ+18 再構成(±5 Myr・1/C(t,d)・二乗則外挿・**G≤12.5 部分集合**"
             f") | **{lam2:.1f} ± {sig2:.1f}** | BJ+18: 19.7±2.2 | n_enc={n_enc:.1f}, "
             f"n_cor={n_cor:.0f}(補正なしなら {lam2_raw:.1f}) |",
             f"| 規約3 FP26 再構成(±0.47 Myr・d<1・サロゲート期待値) | **{lam3:.1f}** | "
             f"FP26: 10.6±4.5(星あたり平均)/ 太陽自身 9.1 | 期待遭遇 "
             f"{n_fp:.2f} 件/0.94 Myr(補正なしなら {lam3_raw:.1f}) |",
             f"| 規約3b FP26 再構成+**離散判定・信頼性カット**(1σ>50%名目で除外) | "
             f"**{lam3b:.1f}** | 同上 | 離散遭遇 {n_disc} 件(unreliable 除外 "
             f"{n_unrel} 件) |", "",
             "## 判定(指示 §2)", "",
             "- 規約3 が FP26 の 9–11 級に接近するか: 期待値版 "
             f"**{lam3:.1f}** / 離散+信頼性カット版(3b)**{lam3b:.1f}** → "
             + ("3b が接近(乖離の主因 = **確率的裾の算入 vs 離散・信頼性判定**の"
                "規約差と同定)" if 6.0 <= lam3b <= 15.0 else
                "両版とも乖離(会計以外の成分 — カタログ構成差等 — が残る)"), "",
             "- 規約2 が BJ の ~19.7 を再現するか: "
             f"**{lam2:.1f}±{sig2:.1f}** → " + ("再現(DR3+検疫済みデータでも高率 — "
             "FP26 の『spurious parallax 主因』説は弱まり、会計・母集団規約差が主因に寄る)"
             if 15.0 <= lam2 <= 25.0 else "非再現(spurious 説と整合の可能性 — 個別監査要)"),
             "",
             "注意(論文反映規律 §4): 規約2 は BJ の**規約**の再構成であり彼らの"
             "カタログの再現ではない(C は GDR2mock 再構成、母集団は DR3 RVS)。"
             "「分裂を説明した」の表現水準は本表+規約対照表の限定付きでのみ用いる。", ""]
    OUT.write_text("\n".join(lines))
    print("\n".join(lines[4:14]))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()

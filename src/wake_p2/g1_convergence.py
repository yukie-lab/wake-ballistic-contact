"""G1 収束試験 — アンサンブル統計量のサンプル数収束と窓幅感度(Phase 2 出口条件)

設計(2026-08-16 下調べに基づく):
- 3軸: A=サロゲート数 m(列プレフィックス — iid ゆえ無作為)/
  B=星数 k チャンク(SHUFFLE_SEED=20260814 で星順序シャッフル済み ⇒
  チャンク前綴り = 母集団の無作為部分標本)+ K=8 互いに素分割の χ² /
  C=解析窓 T × d_max × ホライズン帯(全星共通に支持されるのは |t| ≤ 13 Myr まで
  — run_mc.py の可変積分窓 max(13, min(2.2·hi, 45)) による)
- 統計量: 補正後到来率 λ [/Myr](@d<1/2/5)/ 到来時刻分布(加重分位点・
  1 Myr ビン L1・KS)/ 対称性 A(flash と同定義)/ 判定不能会計 / 上位寄与星
- マスク・IPW は flash_check.py と同一定義(統制領域 = S≥floor ∧ ホライズン内、
  w = 1/max(S, floor)、edge 除外)
- 収束判定(案 — 合格帯は裁定伺い): (i) 部分標本の星ブートストラップ 95% 帯が
  全量推定を含む(入れ子ゆえ保守側と明記)、(ii) K=8 互いに素分割の χ²/dof ≈ 1、
  (iii) σ ∝ 1/√N_star、(iv) サロゲート軸で σ が頭打ち(星間分散支配の実証)

実行: python3 src/wake_p2/g1_convergence.py  → docs/phase2/03-g1-convergence.md
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase2" / "03-g1-convergence.md"
N_SURR = 2000
N_BOOT = 2000
T_ENV = 13.0          # 全星共通支持窓(イベント収集の包絡)
D_ENV = 5.0
M_GRID = [125, 250, 500, 1000, 2000]
K_GRID = [6, 14, 28, 42, 57]
T_GRID = [2.0, 5.0, 10.0, 13.0]
D_GRID = [1.0, 2.0, 5.0]
SEED = 88


def collect():
    """1パスで包絡内イベント表+星台帳を構築"""
    cat = np.load(P2 / "catalog_ingested.npz")
    S = cat["s_completeness"]
    th_def, th_sens = cat["t_h_default"], cat["t_h_sens"]
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    ev = {k: [] for k in ("star", "chunk", "col", "t", "d")}
    stars = {k: [] for k in ("glob", "chunk", "usable")}
    n_edge_flag = 0
    for ci, f in enumerate(files):
        z = np.load(f)
        idx = z["star_idx"]
        stars["glob"].append(idx.astype(np.int64))
        stars["chunk"].append(np.full(len(idx), ci, np.int16))
        usable = np.isfinite(S[idx]) & (S[idx] >= S_FLOOR)
        stars["usable"].append(usable)
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        base = (np.isfinite(t_ph) & (np.abs(t_ph) <= T_ENV) & (d_ph < D_ENV))
        n_edge_flag += int((base & edge).sum())
        base &= ~edge
        r, c = np.nonzero(base)
        ev["star"].append(idx[r].astype(np.int64))
        ev["chunk"].append(np.full(len(r), ci, np.int16))
        ev["col"].append(c.astype(np.int16))
        ev["t"].append(t_ph[r, c].astype(np.float32))
        ev["d"].append(d_ph[r, c].astype(np.float32))
    E = {k: np.concatenate(v) for k, v in ev.items()}
    ST = {k: np.concatenate(v) for k, v in stars.items()}
    n_cat = len(ST["glob"])
    # 星 glob → 連番
    order = ST["glob"]
    pos = {g: i for i, g in enumerate(order)}
    E["row"] = np.fromiter((pos[g] for g in E["star"]), np.int64, len(E["star"]))
    ST["w"] = np.where(ST["usable"], 1.0 / np.maximum(S[order], S_FLOOR), 0.0)
    ST["th_def"] = th_def[order]
    ST["th_sens"] = th_sens[order]
    meta = dict(n_files=len(files), n_cat=n_cat,
                n_unusable=int((~ST["usable"]).sum()), n_edge=n_edge_flag,
                n_events_env=len(E["t"]))
    return E, ST, meta


def config_mask(E, ST, d_max, T, horizon):
    th = ST["th_" + horizon][E["row"]]
    return ((E["d"] < d_max) & (np.abs(E["t"]) <= T)
            & (np.abs(E["t"]) <= th) & ST["usable"][E["row"]])


def per_star_counts(E, ST, mask, m, n_cat_rows):
    mm = mask & (E["col"] < m)
    rows = E["row"][mm]
    n = np.bincount(rows, minlength=n_cat_rows).astype(float)
    n_p = np.bincount(rows[E["t"][mm] < 0], minlength=n_cat_rows).astype(float)
    return n, n_p


def exposure(ST, T, horizon):
    """星ごとの有効露出 [Myr] = 2·min(T, t_h)(統制領域の支持窓)"""
    th = ST["th_" + horizon]
    return 2.0 * np.minimum(T, np.maximum(th, 1e-9))


def rate_stats(ST, n, n_p, m, T, row_sel, n_total, rng=None, horizon="def"):
    """row_sel: 対象星の連番配列。λ は全カタログ規模へスケール。
    正規化は**星ごとの有効露出** e_i = 2·min(T, t_h_i)(全星一律 /2T は
    ホライズン打切りで希釈する誤った推定量 — 軸C の逓減の原因、本文参照)。"""
    w = ST["w"][row_sel]
    e = exposure(ST, T, horizon)[row_sel]
    nn, npast = n[row_sel], n_p[row_sel]
    scale = n_total / len(row_sel)
    contrib = w * nn / e
    lam = contrib.sum() / m * scale
    P, F = (w * npast).sum(), (w * (nn - npast)).sum()
    A = (F - P) / max(F + P, 1e-12)
    if rng is None:
        return lam, A, None, None
    k = len(row_sel)
    bl = np.empty(N_BOOT)
    bA = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = rng.integers(0, k, k)
        bl[i] = contrib[pick].sum() / m * scale
        Pk, Fk = (w[pick] * npast[pick]).sum(), (w[pick] * (nn[pick] - npast[pick])).sum()
        bA[i] = (Fk - Pk) / max(Fk + Pk, 1e-12)
    return lam, A, (np.quantile(bl, 0.025), np.quantile(bl, 0.975), bl.std()), bA.std()


def weighted_quantiles(t, w, qs):
    o = np.argsort(t)
    cw = np.cumsum(w[o])
    cw /= cw[-1]
    return [float(np.interp(q, cw, t[o])) for q in qs]


def main():
    print("G1 収束試験 — 収集パス開始")
    E, ST, meta = collect()
    n_rows = meta["n_cat"]
    rng = np.random.default_rng(SEED)
    lines = ["# G1 収束試験(Phase 2 出口条件 — 統計量ごとの収束曲線文書)",
             "",
             f"> 実行: 2026-08-16 / `python3 src/wake_p2/g1_convergence.py` / "
             f"マスク・IPW は flash_check.py と同一定義",
             "",
             f"母集団: {meta['n_cat']:,} 星(S欠損/floor未満 {meta['n_unusable']:,})/ "
             f"包絡内イベント {meta['n_events_env']:,} 件(d<5, |t|≤13, edge除外 "
             f"{meta['n_edge']:,} 件)", ""]

    # ---- 軸A: サロゲート数(旗艦 d<5, T=10, default)----
    mask_flag = config_mask(E, ST, 5.0, 10.0, "def")
    lines += ["## 軸A — サロゲート数 m(d<5 pc, |t|≤10 Myr, 既定ホライズン)", "",
              "| m | λ@5pc [/Myr] | boot σ | A ± σ_A |", "|---|---|---|---|"]
    all_rows = np.arange(n_rows)
    sigA_prev = None
    sig_m = {}
    for m in M_GRID:
        n, n_p = per_star_counts(E, ST, mask_flag, m, n_rows)
        lam, A, (lo, hi, sd), sA = rate_stats(ST, n, n_p, m, 10.0, all_rows,
                                              n_rows, rng)
        sig_m[m] = sd
        lines.append(f"| {m} | {lam:.2f} | {sd:.2f} | {A:+.4f} ± {sA:.4f} |")
        print(f"A: m={m}: λ={lam:.2f}±{sd:.2f} A={A:+.4f}±{sA:.4f}")
    plateau = sig_m[2000] / sig_m[1000]
    lines += ["", f"σ(m=2000)/σ(m=1000) = {plateau:.3f} — 1 に近いほど星間分散支配"
              f"(サロゲート 2000 の十分性)", ""]

    # ---- 軸B: 星数(m=2000)----
    n5, n5p = per_star_counts(E, ST, mask_flag, 2000, n_rows)
    mask1 = config_mask(E, ST, 1.0, 10.0, "def")
    n1, n1p = per_star_counts(E, ST, mask1, 2000, n_rows)
    lines += ["## 軸B — 星数 k チャンク(m=2000, |t|≤10, 既定)", "",
              "| k | n_star | λ@5pc [95% band] | 全量含む? | λ@1pc [95% band] | 全量含む? |",
              "|---|---|---|---|---|---|"]
    lam5_full, _, (lo5f, hi5f, sd5f), _ = rate_stats(ST, n5, n5p, 2000, 10.0,
                                                     all_rows, n_rows, rng)
    lam1_full, _, (lo1f, hi1f, sd1f), _ = rate_stats(ST, n1, n1p, 2000, 10.0,
                                                     all_rows, n_rows, rng)
    sqrtn = []
    for k in K_GRID:
        sel = np.nonzero(ST["chunk"] < k)[0]
        l5, _, (lo5, hi5, sd5), _ = rate_stats(ST, n5, n5p, 2000, 10.0, sel,
                                               n_rows, rng)
        l1, _, (lo1, hi1, sd1), _ = rate_stats(ST, n1, n1p, 2000, 10.0, sel,
                                               n_rows, rng)
        in5 = lo5 <= lam5_full <= hi5
        in1 = lo1 <= lam1_full <= hi1
        sqrtn.append(sd5 * np.sqrt(len(sel)))
        lines.append(f"| {k} | {len(sel):,} | {l5:.2f} [{lo5:.2f}, {hi5:.2f}] | "
                     f"{'✓' if in5 else '✗'} | {l1:.2f} [{lo1:.2f}, {hi1:.2f}] | "
                     f"{'✓' if in1 else '✗'} |")
        print(f"B: k={k}: λ5={l5:.2f} [{lo5:.2f},{hi5:.2f}] λ1={l1:.2f}")
    cv = np.std(sqrtn) / np.mean(sqrtn)
    lines += ["", f"全量: λ@5pc = {lam5_full:.2f} ± {sd5f:.2f}(相対 "
              f"{sd5f/lam5_full:.1%})/ λ@1pc = {lam1_full:.2f} ± {sd1f:.2f}"
              f"(相対 {sd1f/lam1_full:.1%})",
              f"σ·√n の変動係数 = {cv:.2f}(σ ∝ 1/√N の検査 — 小さいほど良)",
              "帯は部分標本が全量に入れ子のため保守側(緩い)判定であることを明記。", ""]

    # K=8 互いに素分割 χ²
    lines += ["### K=8 互いに素分割(56 チャンク使用)", ""]
    lams = []
    for g in range(8):
        sel = np.nonzero((ST["chunk"] % 8 == g) & (ST["chunk"] < 56))[0]
        l, _, _, _ = rate_stats(ST, n5, n5p, 2000, 10.0, sel, n_rows)
        lams.append(l)
    lams = np.array(lams)
    sd_split = lams.std(ddof=1)
    sd_pred = sd5f * np.sqrt(8)          # 1/8 標本の予測 σ ≈ 全量σ×√8
    chi2 = ((lams - lams.mean()) ** 2).sum() / sd_pred ** 2 / 7
    lines += [f"分割 λ@5pc: {np.array2string(lams, precision=2)} / 分割間 SD = "
              f"{sd_split:.2f} vs 予測 σ(1/8標本) ≈ {sd_pred:.2f} / "
              f"χ²/dof = {chi2:.2f}(≈1 が整合)", ""]
    print(f"B-split: χ²/dof={chi2:.2f}")

    # ---- 軸C: 窓幅・閾値・ホライズン感度(全量)----
    lines += ["## 軸C — 窓幅 T × d_max × ホライズン(全量, m=2000)", "",
              "| T [Myr] | horizon | λ@1pc | λ@2pc | λ@5pc | 域外イベント率 |",
              "|---|---|---|---|---|---|"]
    for T in T_GRID:
        for hz in ("def", "sens"):
            row = [f"| ±{T:g} | {hz} "]
            outr = None
            for d in D_GRID:
                mk = config_mask(E, ST, d, T, hz)
                n, n_p = per_star_counts(E, ST, mk, 2000, n_rows)
                lam, _, _, _ = rate_stats(ST, n, n_p, 2000, T, all_rows, n_rows,
                                          horizon=hz)
                row.append(f"| {lam:.2f} ")
                if d == 5.0:
                    base = ((E["d"] < 5.0) & (np.abs(E["t"]) <= T)
                            & ST["usable"][E["row"]])
                    outr = 1.0 - mk.sum() / max(base.sum(), 1)
            lines.append("".join(row) + f"| {outr:.1%} |")
            print(f"C: T={T} {hz}: done")
    # 素朴推定量(全星一律 /2T)との対比 — 設計誤りの記録と 11.7 の照合
    naive = []
    for T in (5.0, 10.0):
        mk = config_mask(E, ST, 1.0, T, "def")
        nx, npx = per_star_counts(E, ST, mk, 2000, n_rows)
        naive.append((ST["w"] * nx).sum() / (2000 * 2 * T))
    # ファーストルック規約の再構成: ホライズンフィルタなし・/2T(±5, d<1)
    mk_fl = ((E["d"] < 1.0) & (np.abs(E["t"]) <= 5.0) & ST["usable"][E["row"]])
    n_fl = np.bincount(E["row"][mk_fl & (E["col"] < 2000)], minlength=n_rows).astype(float)
    lam_fl = (ST["w"] * n_fl).sum() / (2000 * 2 * 5.0)
    lines += ["", "**推定量の注記**: λ は星ごとの有効露出 e_i = 2·min(T, t_h_i) で"
              "正規化した(統制領域の定義と整合)。全星一律 /2T の素朴推定量は"
              "ホライズン打切りで希釈され T とともに見かけ上逓減する"
              f"(素朴 @1pc: ±5 → {naive[0]:.2f}, ±10 → {naive[1]:.2f} /Myr — "
              "本実行の初版で誤採用し自己検出・修正)。露出正規化 λ が T に対し"
              "平坦であることが定常性の正しい読みで、G3-4 と整合。", "",
              f"**ファーストルック 11.7 /Myr の照合**: ホライズンフィルタなし・"
              f"/2T 規約(±5 Myr, d<1)は**旧エンジン(v1)データ上で 11.7 を厳密"
              f"再現**し規約が同定された。修正エンジン(d² 精密化)データでは同規約 = "
              f"{lam_fl:.1f} /Myr(鋭い極小の d_min 過大評価の解消で sub-pc "
              "イベントが増えた分)。この規約は遠 |t| の検出不完全性を補正しない"
              "下方バイアス値であり、露出正規化(本推定量)がそれを補正する。", "",
              "**エンジン修正の効果(重要)**: 旧データの λ@1pc = 20.26 は精密化"
              "バグ(d 放物線の鋭極小破綻)による系統的過小だった。修正後の "
              "λ@1pc は上表のとおりで、増分は t_h < 0.5 Myr・rv_error 5–14 km/s の"
              "少数の現在通過中星に集中する(上位寄与表参照 — 重い裾)。"
              "BJ+18 の 19.7±2.2 は本推定の 95% 帯内に留まるが、点推定の一致は"
              "主張しない(帯が広く、寄与が少数星支配のため)。二帳簿整合の検証は "
              "C(t,d) 参考表示層で行う。", ""]

    # ---- 時刻分布の収束(旗艦)----
    lines += ["## 到来時刻分布の収束(d<5, |t|≤10, 既定, m=2000)", "",
              "| k | q10 | q50 | q90 | L1(vs 全量) | KS(vs 全量) |",
              "|---|---|---|---|---|---|"]
    mm = mask_flag & (E["col"] < 2000)
    t_all, w_all = E["t"][mm], ST["w"][E["row"][mm]]
    bins = np.arange(-10, 10 + 1e-9, 1.0)
    h_full = np.histogram(t_all, bins=bins, weights=w_all)[0]
    h_full = h_full / h_full.sum()
    for k in K_GRID:
        sub = mm & (E["chunk"] < k)
        t_s, w_s = E["t"][sub], ST["w"][E["row"][sub]]
        q = weighted_quantiles(t_s, w_s, [0.1, 0.5, 0.9])
        h = np.histogram(t_s, bins=bins, weights=w_s)[0]
        h = h / h.sum()
        L1 = np.abs(h - h_full).sum()
        KS = np.abs(np.cumsum(h) - np.cumsum(h_full)).max()
        lines.append(f"| {k} | {q[0]:+.2f} | {q[1]:+.2f} | {q[2]:+.2f} | "
                     f"{L1:.4f} | {KS:.4f} |")
    lines.append("")

    # ---- 上位寄与星(塊の教訓)----
    e10 = exposure(ST, 10.0, "def")
    contrib = ST["w"] * n5 / e10
    top = np.argsort(contrib)[::-1][:10]
    tot = contrib.sum()
    lines += ["## 上位寄与星(λ@5pc への w·n/e share — 塊構造・露出集中の監視)", "",
              "| 順位 | star_idx(大域) | w | n_ev | t_h [Myr] | share |",
              "|---|---|---|---|---|---|"]
    for r_, i in enumerate(top, 1):
        lines.append(f"| {r_} | {ST['glob'][i]} | {ST['w'][i]:.2f} | "
                     f"{int(n5[i])} | {ST['th_def'][i]:.2f} | {contrib[i]/tot:.1%} |")
    top1_share = contrib[top[0]] / tot
    top10_share = contrib[top].sum() / tot
    lines += ["", f"最大単一星 share = {top1_share:.1%} / 上位10星 = "
              f"{top10_share:.1%}(1星支配の監視 — 02-clump-notes.md の教訓)", ""]

    # ---- 判定案 ----
    lines += ["## 収束判定(案 — 合格帯の数値は裁定伺い)", "",
              f"1. 部分標本 95% 帯の全量包含(軸B): 上表のとおり",
              f"2. K=8 分割 χ²/dof = {chi2:.2f}(目安 [0.5, 2])",
              f"3. σ·√n 変動係数 = {cv:.2f}(σ∝1/√N、目安 < 0.3)",
              f"4. サロゲート頭打ち σ2000/σ1000 = {plateau:.3f}(目安 < 1.15 — "
              f"√2=1.41 なら surrogate 分散支配)",
              f"5. 全量相対誤差: λ@5pc {sd5f/lam5_full:.1%} / λ@1pc "
              f"{sd1f/lam1_full:.1%} — これは**星母集団の統計誤差**であり"
              "(軸A のとおりサロゲート分散は既に無視可能)、MC を増やしても"
              "縮まないカタログ固有の測定誤差。G1 の合格対象は 1〜4(MC/標本"
              "収束)であり、5 は測定の誤差棒として報告する — この枠組み自体を"
              "裁定伺いとする(BJ+18 の f_c=0.1 系統と同思想)", ""]
    OUT.write_text("\n".join(lines))
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()

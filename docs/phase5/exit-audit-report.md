# Phase 5 出口条件監査報告 — 三点セット監査+再現性検証(裁定#20 手順1)

> 2026-08-16 実施。両条件 PASS。検査器はコミット済み・再走可能。

## 1. 三点セット監査: PASS(全32項目)

実行: `python3 scripts/audit_three_artifacts.py`

- **A. 論文 ⇄ JSON(18項目)**: 看板数値は全て公開 JSON から再導出と一致 —
  λ(1/2/5pc)=4.485/27.534/137.303(論文丸め 4.49/27.5/137.3)、CI95
  [1.78, 8.50]、f*(3.07)=5.03e-3→5.0e-3、f*(1pc)=6.75e-2→6.8e-2、橋 5.3、
  Δv 5.93/5.85、ノード 646、カタログ 2,197、GJ710 +1.2943 Myr/0.0519 pc、
  HD7977 0.0367 pc/−2.7609 Myr、地図版 1.0.1、三値凡例 3+3、E9 帯 1.5–2.0、
  直接通過2件。
- **B. シミュレータ ⇄ 論文(10項目)**: ハーネス期待値(16検査 = 名前付き13+
  sha256×3)が論文数値と同一。
- **C. シミュレータ ⇄ JSON(4項目)**: sim/data = data/release = MANIFEST
  (sha256 全一致)。
- **実フレーム確認**: 公開 Pages(https://yukie-lab.github.io/wake-atlas/)で
  ハーネス画面「all 16/16 PASS」を実ブラウザ表示で確認(sha256 3件は
  b65182b3… / 6e0dfa60… / d5286341… — release と同一)。

## 2. 再現性検証(クリーン環境): PASS

手順(全て再実行可能):

1. クリーン clone: `git clone`(HEAD = 5bdaf4c)→ 一時ディレクトリ
2. 新規環境: `conda env create -f environment.yml`(python 3.12.13 /
   numpy 2.5.2 — environment.yml のピン留めどおりに解決)
3. 実測データ持込: `data/{p2,p3,p4,phase_r}`(誤差 MC 産物・中間 npz。
   git 管理外 — 本検証の対象はコード+環境の再現性)
4. 公開物再生成: `event_catalog.py` → `exclusion_map.py` →
   `flyby_network.py` → `paper_figs_main.py`
5. 照合: 再生成 3 JSON の sha256 が data/release と**ビット一致**
   - arrival_catalog_v1.json = b65182b3d6db5860…
   - exclusion_map_v1.json = 6e0dfa604d2d0fce…
   - flyby_network_v1.json = d5286341463e75d0…
6. 論文: クローン内で `gate_check_paper.py` — コンパイル両版 PASS
   (図5点もクローン内で再生成)

適用範囲の明示(誠実性): 本検証は「アーカイブ済みコード+ピン留め環境+
実測中間データ」からの公開物の決定論的再生成を確認した。上流(Gaia
アーカイブ取得 `scripts/fetch_*.py`・誤差 MC `run_mc.py`(シード固定・
一晩級))は再実行手順がリポジトリに文書化されており、G1 収束試験で検証済み
だが、本監査では計算予算の理由で再走していない。

## 3. 付随修正

- 論文付録D(日英)に公開シミュレータ URL を追記 → 再コンパイル+7ゲート
  再走 全PASS(数値集合 98/98 一致を維持)

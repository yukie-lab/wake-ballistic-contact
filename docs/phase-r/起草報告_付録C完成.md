# 起草報告 — 数学論文 付録C 完成(arXiv 自己完結版 = Zenodo v2 投稿稿)

> 2026-08-17 / 起草指示書 v1.1(裁定ログ#21)の実行報告 / 実行: Claude Code (Fable 5)
> 対象: docs/phase-r/paper/paper.tex → paper.pdf(25頁、コンパイル・参照解決クリーン)
> 憲法遵守: 新規の数学的主張は追加していない(編纂・展開のみ)。判断を要した点は
> 本報告「参謀確認事項」に列挙し裁定系に上げる。

## 完了した作業(指示書 §1〜§7)

1. **C.1 定理A**: プレースホルダ → 完全証明(約2頁)。claims.md 審査サイクル1
   受理版のみをソースとし、(a) 世代帰納+親子木整礎性 (b) 決定的試行時刻再帰
   t_j = max(inf T_j, m_{j−1})、m_j = t_j+τ(種の境界規約 m₀=0 を明示)+
   τ 不寄与の明記 (c) カプセル体積補題(Lemma 1、進入時刻一意 ⇒ 重複勘定なし)
   (d) multivariate Mecke+Tonelli の**等号** (e) Hilbert–Schmidt ⇒ 自己共役
   有界 ⇒ ⟨𝟙,K^k𝟙⟩ ≤ r(K)^k ⇒ Σ 収束 ⇒ a.s. 絶滅。Krein–Rutman 不使用。
2. **C.2 定理B**: 1段落の完全証明。窓 [0,∞)/空 → 即時試行 → 遅延=時刻シフト →
   クラスター同一視(探索で各対は片方向のみ消費)の4要素。「事象の同値」語法維持。
3. **C.3 定理C2**: c2-proof-final.md §0〜§8 を C.3.1〜C.3.8 に完全転写
   (parameters/lattice → geometry contract → erosion patch → disclosure
   capsule → normalization bridge → Lemma X → same-branch flux → assembly)。
   assembly 内に独立段落 **"Identification of the comparison lattice"** を新設
   (裁定#10 修正2-§6.6 消化): 原典の定式化、同型 φ(x,y)=(x−y,x+y)、錐内完結性、
   Bernoulli 保存、Theorem 1(b) の (p,q)=(α,α) 適用を明文化。
   数値は付録A認証表(\label{app:certtable} 新設)への \ref 一元管理とし、
   スポット審査独立再現値(66.5R³ / 1.569 / 2.645×10⁻⁸ / 7.79)を C.3.5 に採録。
4. **C.4 C6a/C6b′**: 完全証明化。C6a は明示化3点(v₀ 条件付け、等方性消費点、
   遭遇=試行3点根拠+o(t) 粒子ごと定数)込み。C6b′ は望遠鏡式会計+整礎性+
   τ=0 病理を自己完結化、死マーク粒子適用の一文・決定的半径の副産物を保持。
   前線半径 R(t) の定義文を C.4 冒頭に追加(未定義記号ゼロのため)。
5. **C.5 定理D**: 本文証明+スケール不変性補題(Lemma 7)を付録に吸収。
   スポット審査3点(補題明示・0<ρ・R=1 正規化)反映。
6. **フォーク6改称**: §1 → "Claim (the SIR bound does not extend — numerically
   certified, experiment E8c; Section 4)"、§4 → "Claim (reverse channel —
   numerically certified, experiment E8c)"。強度記述(certified violation of
   the expectation bound / does not by itself prove survival)は不変(grep 確認)。
7. **C系列番号脚注**: §1「Main results」見出しに指示書 §7 の文面どおり追加
   (Appendix B / Section 10 / Section 8 は \ref で解決)。

## Liggett (1995) 原典照合(指示書 §3 必須)

- Project Euclid 公式 PDF を取得し全文照合。**判定: 一致(明示同型を介して
  引用正当)— 不一致なし、起草続行**。
- 台帳: `docs/phase-r/liggett95-collation.md`(原典文言引用・同型写像・
  Theorem 1(b) 適用の等号成立まで記録)。

## 検収(指示書 §8 → gate_check_mathpaper_c.py 恒久化)

- スクリプト: `scripts/gate_check_mathpaper_c.py` / ログ:
  `docs/phase-r/paper/gate-check-c.log` — **全ゲート PASS**。
- G1: tectonic コンパイル通過(未定義参照・引用ゼロ)。付録C内の
  "bundled repository" / "wake-repo-v1.tar.gz" / "c2-proof-final.md" /
  "claims.md" 残存 0件(§9・付録A の方法参照は仕様どおり残置)。
- G2(機械部分): 指定9定数(T_a=T_s/32, T_g=64(τ+T_s), 200分割,
  ū_x=w̄/√(17/16), a=ū_xT_g/32, ℓ_y=8a, θ*=s*/(1.05w̄), N_h=⌈βμ/16⌉,
  M=⌈2μ⌉)の転写一致を grep 検査。補題依存グラフ:
  L1(カプセル)→(C.1)/ L2(幾何)→ L3(パッチ)/ L4(開示)→ L5(橋)/
  L4+L5+L6(X)→ flux → assembly / L7(スケール)→(C.5)— 循環なし。
  ただし L4 証明(ii)に L6 への前方参照(スコープ注記であり論理依存ではない —
  ソース補題2の構造どおり)。参謀通読での確認対象。
- G3: 付録A表(7.82 / 0.00483 / 1.688×10⁻⁹ / 2.640×10⁻⁸)と C.3 参照値
  (7.8 / 0.0048)の一致、スポット審査独立再現値の採録を機械検査。
- 脚注・改称の反映も grep 検査に組込済み(ゲート2)。

## arXiv AI ポリシー事前確認(指示書 §9.3)

2026年時点の arXiv 方針: (i) AI は著者になれない(著者=前田さんで整合)、
(ii) 著者が内容に全責任(§9 "The author takes full responsibility" と整合)、
(iii) 未検証 AI 生成コンテンツ(幻覚引用・捏造参照・残存プロンプト等)への
1年 BAN 制度(2026 新設)。本論文は引用の機械検証ログ+Liggett 原典照合+
付録Bの三層検証開示で整合。**付録Bの開示文の変更は不要と判断**(投稿直前に
最終再確認を推奨 — 従前どおり)。

## 参謀確認事項(裁定系へ — 実装では解決していない)

1. **表題の版表記**: "(Preprint --- Zenodo v1, doi:...)" を
   "(Preprint --- Zenodo v2; v1: doi:10.5281/zenodo.21955413)" に更新した。
   v2 の版 DOI は付与後に判明するため v1 DOI を残す形式を採用。要承認。
2. **Lemma X の (1−δ) 係数**: c2-proof-final.md §6 の主張文には (1−δ) が
   あるが δ は未定義。正典序列上位の claims.md セッション4 補題0
   (一様下界 e^{−(t*−α)/T_s} — 係数なし)に従い、観察1〜3が実際に与える
   クリーンな下界で記載した(打切超過は開ビットの Chernoff 余裕が吸収、
   と明示)。要確認。
3. **C6a の等方性**: 受理記録の明示化(2)は等方性を消費するが、本文の
   定理文(unbounded support のみ)には等方性仮定が明示されていない。
   付録は記録どおり「等方性の消費点」を明記した(非等方原子的 ν では
   当該ステップが破綻しうる旨も記録どおり)。**定理文への等方性追加の要否は
   文言変更につき裁定へ**。
4. **定理B と生存定義の細部**: §2 の定義「全時刻で生存マーク集合非空」を
   文字通り取ると、静的極限では「飛行中マークのみ生存者ゼロ」の瞬間が
   正確率で生じうる。証明は本文の「事象の同値(up to null sets)」の語法に
   合わせ「非有界時刻で生存マークが存在」で閉じた(C2 は被覆条項により
   強い意味でも成立)。§2 の一語調整("at arbitrarily large times")の
   要否は参謀判断へ。
5. **箱幅の表記**: c2-proof-final.md「箱幅 a」と本文「boxes of side 2a」の
   表記差は、本文(公開版)の "side 2a(半幅 a)・コア半幅 a/2" を正とした。
6. **"eight-branch premise"(8分岐の前提)**: ソースの文言をそのまま転写。
   用語の展開が必要なら参謀通読で指摘を仰ぐ。

## 後工程(指示書 §9 — 未実行・順序どおり)

参謀最終通読(G2/G3)→ 前田さん承認 → **Zenodo New version で v2**
(新規レコード禁止・concept DOI 維持、改版理由: 「付録Cの自己完結化・
ラベル精密化・脚注追加。数学的内容の変更なし」)→ 同一 PDF で arXiv 投稿。
WAKE 本体 v2 での arXiv ID 併記(裁定確定済み)は番号取得後。

---

疑義がある場合は実装で解決せず、参謀チャット経由で裁定に上げること(従前どおり)。

# Liggett (1995) 原典照合台帳 — 付録C.3「格子の同定」段落(裁定#10 修正2-§6.6 消化)

> 2026-08-17 / 起草指示書 v1.1 §3 必須タスク / 照合実施: Claude Code (Fable 5)
> 原典: T. M. Liggett, "Survival of discrete time growth models, with applications
> to oriented percolation", *Ann. Appl. Probab.* **5**(3):613–636, 1995.
> doi:10.1214/aoap/1177004698 — Project Euclid 公式 PDF を取得し全文照合。

## 照合項目と原典文言(引用)

| # | 項目 | 原典文言(literal) | 頁 |
|---|---|---|---|
| 1 | 成長連鎖の定義 | 整数の有限部分集合上の離散時間 Markov 連鎖 A_n、0 ≤ p ≤ q ≤ 1: "Given A_n, the events {x ∈ A_{n+1}} are conditionally independent, and P(x ∈ A_{n+1} \| A_n) = q, if \|A_n ∩ {x, x+1}\| = 2; p, if \|A_n ∩ {x, x+1}\| = 1; 0, if \|A_n ∩ {x, x+1}\| = 0." | p.613 |
| 2 | 定理1 | "THEOREM 1. (a) Suppose q < 2(1−p). Then A_n dies out. (b) Suppose 1/2 < p ≤ 1 and q ≥ 4p(1−p). Then A_n survives."(survives = P(A_n ≠ ∅ ∀n) > 0) | p.614 |
| 3 | 有向パーコレーションの定義 | "letting the sites (or bonds) of Z² be labeled open or closed with probability α and 1 − α, respectively. Percolation is said to occur if the probability is positive that there is an infinite oriented (in the positive x and y directions) path starting from the origin which passes only through open sites (or bonds)." | p.614 |
| 4 | 同定と 3/4 上界 | "think of the 'time' n as corresponding to the sites (x, y) ∈ Z²₊ which satisfy x + y = n, and of A_n as the set of sites with this property which can be reached from the origin through open sites (or bonds). Then the identification is exact, provided that we take q = p = α in the site case … Since (p, q) = (3/4, 3/4) satisfy the assumptions of part (b) of Theorem 1, we obtain the upper bounds 2/3 and 3/4 for the critical values in these two cases." | p.615 |

## 我々の格子(paper.tex §6.3 組立 / 付録C.3)

ℒ = {(n,k) ∈ ℤ×ℤ_{≥0} : n+k 偶}、有向辺 (n,k) → (n±1, k+1)、種サイト (0,0)、
サイト独立開確率 1−ε(開性はサイトのみの性質)。

## 照合結果

**判定: 一致(明示的な有向グラフ同型を介して引用は正当)— 不一致なし、起草続行。**

1. **同型写像**: φ(x, y) := (x−y, x+y) は ℤ²₊ を錐 {(n,k) ∈ ℒ : |n| ≤ k} に全単射で
   写す(n+k = 2x は偶、逆写像 x = (n+k)/2 ≥ 0, y = (k−n)/2 ≥ 0)。ステップ
   (x,y)→(x+1,y) は (n,k)→(n+1,k+1) に、(x,y)→(x,y+1) は (n,k)→(n−1,k+1) に、
   原点は種サイト (0,0) に写る — 隣接構造は正確に対応。
2. **錐内完結性**: ℒ 上の種からの有向路は 1 ステップで |n| が ±1・k が +1 する
   ため錐 {|n| ≤ k} を出ない。ゆえに種からの到達可能性の判定は錐内で完結し、
   φ は当該部分グラフの有向グラフ同型。
3. **測度の保存**: i.i.d. Bernoulli サイト開閉は全単射 φ で i.i.d. Bernoulli の
   まま移送される。
4. **定理の適用**: (p,q) = (α,α) は α = 3/4 で Theorem 1(b) の条件(1/2 < p ≤ 1、
   q ≥ 4p(1−p) = 3/4 は等号)を満たし、α > 3/4 では真の不等号で満たす。ゆえに
   α ≥ 3/4 の全域でパーコレーションが直接従い、開確率 1−ε > 3/4 ⇒ 種サイトの
   無限開有向クラスタが正確率 — 本構成の使用形と一致。
5. **文言差の注記**: 原典の連鎖定義(項目1)は親集合 {x, x+1} 規約(対角座標での
   添字付け)であり (n±1) 規約と座標系が異なるが、原典自身が項目4で連鎖と
   percolation の同定を "exact" と明示している。本照合は percolation 定式(項目3)
   に対して行い、文言レベルの座標差は上記 φ で完全に吸収される。

## 帰結(起草への反映)

- 付録C.3 組立節に独立段落 "Identification of the comparison lattice" を新設し、
  原典の定式化・φ の定義・錐内完結性・Bernoulli 保存・Theorem 1(b) の
  (p,q)=(α,α) 適用を明文化(裁定#10 修正2-§6.6 の消化)。
- 本文 §6.3 の既存文 "the same adjacency structure … we verified the
  identification of the two lattices explicitly" は付録の明示同型により
  裏付けられる(本文変更なし)。

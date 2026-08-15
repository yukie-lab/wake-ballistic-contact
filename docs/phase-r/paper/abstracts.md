# Zenodo v1 説明欄用アブストラクト(日英 — 裁定ログ#10 組立仕様1)

## English

Motivated by observed stellar kinematics, we introduce a contact process on
particles moving ballistically in R³: a Poisson point process whose points
carry i.i.d. velocities, with entry-driven fire-and-forget transmission at
range R (success probability p, delay τ, each ordered pair attempts at most
once ever), Exp(T_s) lifetimes, and re-marking allowed. We establish: (A) an
extinction theorem via the spectral radius of an explicit velocity transfer
kernel (SIR variant; the moment computation is exact); (§4) that this
branching-type bound does not extend to the full model — a "reverse channel"
(a child re-marks its dead parent) produces a certified 4.4σ excess of the
expected total progeny N (mark events including the seed) over the branching
bound; (B) that in the static limit the survival event coincides
with percolation of a bond-diluted random geometric graph; (C2, main result)
a survival theorem for the full model, proved by a cell–relay
renormalization with machine-certified geometry (interval arithmetic,
including a normalization bridge between accepted and disclosed candidate
sets), a private-coin coupling lemma, and comparison with oriented site
percolation; (D) that at densities where static geometry forbids percolation
for every p, sufficiently fast motion enables colonization; (C6a/C6b′) a
superlinear/linear front dichotomy. Numerically we establish a convention
dichotomy: under entry-driven transmission, motion helps monotonically;
under dwell-time requirements, an optimal speed emerges. All proofs were
developed under a three-layer verification protocol (independent numerical
falsification, eleven cycles of adversarial line-by-line review by fresh AI
instances, machine certification), fully disclosed in the appendices; this
internal verification is not a substitute for human peer review.

## 日本語

実測恒星運動学を動機として、等速直線運動する Poisson 粒子系上の接触過程
(進入駆動・撃ちっ放し・対一回・再マーク許可、到達半径 R、成功確率 p、遅延 τ、
寿命 Exp(T_s))を導入し、その臨界構造を確立する。主結果: (A) 速度転送核の
スペクトル半径による絶滅定理(SIR 版・モーメント計算は厳密)、(§4) この分枝型上界が
完全モデルには拡張されないこと — 「逆向きチャネル」(子が死んだ親を再マークする経路)
により期待総子孫数(N = 種を含むマーク事象総数)が分枝上界を 4.4σ で
超過することの数値確定、(B) 静的極限の生存事象がボンド希釈
ランダム幾何グラフのパーコレーションと一致すること、(C2・主結果) 完全モデルの
生存定理 — セル・リレー繰り込み(幾何は区間演算で機械認証、受理/開示集合の正規化橋を
含む)+私有コイン結合補題+方向付きサイトパーコレーション比較、(D) 静的幾何が
すべての p でパーコレーションを禁じる密度でも、十分速い運動が入植を可能にすること、
(C6a/C6b′) 前線の超線形/線形二分。さらに数値的に「規約二分法」を確立する:
進入駆動では運動は単調に助け、滞在時間要求型では最適速度が現れる。全証明は三層の
検証プロトコル(独立数値反証・新規 AI インスタンスによる11サイクルの行単位敵対審査・
機械認証)の下で作成され、付録で全面開示する。この内部検証は人間の査読の代替ではない。

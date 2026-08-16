# 露出会計 — 一次資料引用の保全版(調査 2026-08-17、ar5iv/arXiv HTML 経由)

> 対照表(exposure-accounting.md)の根拠引用。A&A 出版版は 403 のため arXiv 版。
> 節番号帰属に軽微な転記リスク(要所はクロスチェック済み)。

## BJ+18 (arXiv:1805.07581) 根拠引用

- (A) 露出: "Within the window |tph|<5 Myr, dph<5 pc we have nenc = 463.4 …
  ncor = 4914±542 encounters, which corresponds to 491±54 encounters per Myr
  within 5 pc."(§4.3)/ "We instead scale the value found for 5 pc using the
  expectation that the number of encounters within some distance grows
  quadratically with distance… 19.7±2.2 Myr⁻¹ [within 1 pc]."
  検算: 4914/10 = 491.4、491×(1/5)² = 19.7 ✓
- (B) 打切り: "The fractional number of encounters observed in a window, nenc,
  is just the sum of the fraction of all surrogates per star which lie in that
  window."(§4.3)/ "Large uncertainties in the data … are accommodated by the
  resampling"(§2.2)/ 窓選択の明文理由なし: "The effective time limit of this
  study is 5–10 Myr."/ 感度: ±2.5 Myr で 373±44 @5pc
- (C) 判定不能: フィルタ "u<35 and visibility_periods_used ≥ 8"(3379 星)/
  "We do not remove bogus encounters, as their number is small."/
  "Spuriously large parallaxes … would tend to inflate both the number of
  encounters found and this inferred rate. The magnitude of this effect is
  hard to quantify."(過大方向の自認)
- (D) C: "The ratio of these two distributions gives the completeness map,
  C(tph,dph)"(§4.1)/ モック銀河 = Galaxia(Besançon 型、3 kpc 距離カットのみ)、
  観測側 = "phot_g_mean_mag <= 12.5 AND teff_val > 3550 AND teff_val < 6900"/
  "average value (over the bins) of 0.09 for |tph|<10 Myr and 0.14 for
  |tph|<5 Myr"/ 適用 = 分子に 1/C(実効 C = 463.4/4914 ≈ 0.094)/
  ゼロセルは近傍平均置換、−15〜+15 Myr × 0–10 pc で構成+平滑フィット

## FP26 (arXiv:2605.16496) 根拠引用

- (A) 露出: "tlim … 0.47 Myr for … 25 pc boundaries"(§3、v90 由来の一律窓)/
  "A total of 3 765 systems are within the distance limit of llim = 25 pc and
  were selected as central stars"/ 率鎖: 16,534 遭遇 → 束縛系処理後 15,733 →
  "the median number of close encounters within the considered 0.94 Myr total
  time interval is 7.0±3.0" → ÷0.70 → "10.6±4.5 per Myr and star"
  検算: 7.0/0.94/0.70 = 10.64、3.0/0.94/0.70 = 4.56 ✓(±4.5 は系間分散の伝播)
  太陽: "the Sun experiences six close encounters within the same time and
  distance limits … at the mode of the distribution"(→ 6/0.94/0.7 = 9.1)
- (B) 打切り: "For wider temporal windows, however, the uncertainty in
  periastron distance increases…"(採択確率低下)+ 高速星の見逃し
  ("EGGR 290")→ 一括 ÷0.70 で処理。星ごとの有効窓なし
- (C) 判定不能: "Cases where the 1σ uncertainty exceeds 50% of the nominal
  periastron distance were deemed unreliable and thus excluded."/ 束縛系:
  "we treated the system as one single object"(連星54)、CPMP は内部遭遇を
  統計から削除 / RUWE カットなし / plx/err>5・RV 必須
- (D) C: "By integrating the distribution shown in Fig. 6(b), we find that our
  calculations currently capture 70% of the encounters."(一律 0.70、自己分布
  vs 一様)/ カタログ完備性 "at 50 pc, our catalogue contains 91% of the
  stars" は率に未反映
- (F) BJ との差: "We therefore attribute the higher rate reported by
  [Bailer-Jones et al. 2018] mainly to the effect they acknowledge: imperfect
  filtering of spurious parallaxes"(定量分解なし)/
  "The lower rate we find cannot be entirely attributed to the more
  restrictive spatial (25 pc) and temporal (±0.47 Myr) limits … nor to the
  incompleteness caused by missing very fast encounters"
  注意: FP26 は BJ の率窓を "within 15 Myr" と記載(実際は ±5 Myr — 齟齬)

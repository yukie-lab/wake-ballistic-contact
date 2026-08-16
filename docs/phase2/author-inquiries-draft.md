# 著者照会 文面ドラフト(裁定ログ#12 次アクション3 — 参謀チャット経由・送付は前田さん最終確認後)

> 表現規律(裁定ログ#11 裁定5): 断定を避け対話の水準で。**反証は論文で、照会は対話で。**
> 送付タイミング: Phase 2 完了済み → 参謀通読 → 前田さん最終確認後。

## Draft 1 — To the Gaia DR2 encounters team (BJ+18, arXiv:1805.07581)

Subject: Questions on the accounting conventions in your DR2 encounter-rate analysis

Dear Dr. Bailer-Jones and colleagues,

We are preparing a study of stellar encounter statistics on Gaia DR3 with an
independent completeness treatment (inverse-probability weighting over the RVS
selection function, with per-star effective exposure windows). In reconstructing
your 2018 analysis for comparison, a few points were not fully determinable from
the text, and we would be grateful for clarification:

1. Was there a specific rationale for the ±5 Myr rate window (beyond the
   effective 5–10 Myr time limit noted in the paper)?
2. Does the Galaxia-based mock Galaxy include white dwarfs, brown dwarfs, and
   unresolved binaries in the completeness normalization?
3. Are losses induced by the astrometric quality filters (u < 35,
   visibility_periods_used ≥ 8) intended to be absorbed by C(t_ph, d_ph), or
   are they outside its scope?
4. Were any cuts applied on radial-velocity values or uncertainties?
5. Could you share the bin widths and the smoothing/fit form used for the
   completeness map?

For context: applying your convention (±5 Myr window, 1/C weighting, quadratic
scaling from 5 pc) to our DR3 sample restricted to G ≤ 12.5 yields
23.7 ± 2.6 Myr⁻¹ within 1 pc, consistent with your 19.7 ± 2.2. Our
reconstruction suggests that much of the difference between published rates in
the literature may trace to accounting and population conventions rather than
data quality; we would value your view on this reading.

## Draft 2 — To the FP26 team (arXiv:2605.16496)

Subject: Questions on the encounter-rate conventions in your DR3 study

Dear Dr. Fernandez-Puig and colleagues,

We are preparing an encounter-statistics study on Gaia DR3 and reconstructed
your accounting conventions for comparison. A few points were not fully
determinable from the text:

1. In "per Myr and star", is each encounter attributed to both members of the
   pair or to one? (Our arithmetic suggests both-member attribution.)
2. For the GJ 710-class rate 0.0210 ± 0.0018, we could not reproduce the
   denominator from the stated 3656.36 average stars and 0.94 Myr span
   (we obtain 0.0236); could you clarify?
3. Do the acceptance rule (lower 1σ bound < 1 pc) and the reliability cut
   (1σ > 50% of nominal excluded) apply to the full star–star statistics of
   16,534 encounters, or to the solar-encounter analysis only?
4. Is the ±4.5 uncertainty the propagated inter-system scatter of Fig. 5?
5. Was there a rationale for not applying the catalogue spatial completeness
   (91% at 50 pc) to the rate?
6. How does the v ≈ 122 km/s completeness limit relate to the 90th-percentile
   velocity used to derive t_lim?
7. We read the BJ+18 rate window as ±5 Myr rather than "within 15 Myr" — is
   the latter intended differently?

For context: our reconstruction of your convention on our DR3 sample yields a
higher value, which we can trace substantially to faint stars
(G ≳ 14) with |RV| ≳ 150 km/s but disk-like tangential motion; when we
restrict to bright stars the values approach yours. Our reconstruction
suggests the difference from BJ+18 may be dominated by the population that the
completeness correction targets (full mock population vs. catalogue
population) rather than by residual spurious parallaxes; we would value your
view on whether this reading is consistent with your attribution.

## Draft 3 — To the author of the DR3 GJ 710 parameters (BB22)

Subject: Possible unit interpretation in the GJ 710 perihelion time

Dear colleague,

In comparing published GJ 710 perihelion parameters we noticed that your
reported t_ph = 1.324 ± 0.026 Myr equals (to 0.1%) our and other groups'
1.294 Myr when divided by 0.97779 = Myr/(pc·(km/s)⁻¹), i.e., it matches a
perihelion time expressed in pc/(km/s) units. Could this be a unit conversion
at play? We ask because our DR3 reproduction (numerical orbit integration and
LMA) yields 1.294 Myr, 0.0503 pc, in agreement with de la Fuente Marcos &
de la Fuente Marcos (2022) and your distance value. We would welcome your
view before we discuss the comparison in print.

---

各ドラフト共通の添付: 規約対照表(exposure-accounting.md の英訳版)+
カタログ v1 の該当率ブロック。送付順: BB22(単純・善意の確認)→ BJ → FP26。

# WAKE: a visitation-statistics atlas of the solar neighbourhood

**Arrival statistics, an exclusion map, and a flyby network on Gaia DR3 kinematics**

Yukie Maeda ([ORCID 0009-0005-3401-9230](https://orcid.org/0009-0005-3401-9230)) — Independent Researcher, Tokyo

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21966305.svg)](https://doi.org/10.5281/zenodo.21966305)

Should we have been visited? This repository carries the full WAKE atlas:
the bilingual paper (English authoritative, Japanese translation), the
released data set, and the browser simulator.

- **Paper**: `docs/phase5/paper/wake_en.pdf` / `wake_ja.pdf`
- **Data**: `data/release/` — `arrival_catalog_v1.json` (2,197 arrival
  events, schema v1.1), `exclusion_map_v1.json` (v1.0.1),
  `flyby_network_v1.json`, with a SHA-256 `MANIFEST.json`
- **Simulator**: https://yukie-lab.github.io/wake-atlas/ — reads exactly the
  released JSONs; its first artifact is a 16-check verification harness
  (paper numbers + SHA-256 digests) shown before any visualization

## Headline numbers (conditional statements over a declared population)

- Clean arrival rate λ(1 pc) = 4.5 (+4.0/−2.7) per Myr (FGK + early-M,
  completeness-corrected); the published factor-of-two split is dominated by
  completeness-target population choices, not data quality
- Exclusion map: f* = 5.0×10⁻³ at the standard probe range of 3.07 pc —
  above that settled fraction, the solar system should have been visited
  within the past 10 Myr (silence rejected at 95%)
- Flyby network: a propellant-minimal visiting route exists at all times,
  Δv ≈ 5.8 km/s (single transfer)

This is surveying, not proof: every statement is a conditional probability
statement, and undecidable regions are reported as undecidable.

## Reproduction

```bash
conda env create -f environment.yml && conda activate wake
python3 src/wake_p2/event_catalog.py     # arrival catalogue
python3 src/wake_p3/exclusion_map.py     # exclusion map
python3 src/wake_p4/flyby_network.py     # flyby network
python3 src/wake_p5/paper_figs_main.py   # all five figures
python3 scripts/gate_check_paper.py      # 7 quality gates
python3 scripts/audit_three_artifacts.py # paper<->data<->simulator audit
tectonic docs/phase5/paper/wake_en.tex   # compile (likewise wake_ja.tex)
```

Upstream inputs (Gaia DR3 fetch, seeded error-MC) regenerate via
`scripts/fetch_*.py` and `src/wake_p2/run_mc.py`; the clean-environment
verification record is `docs/phase5/exit-audit-report.md`.

## Companion mathematics paper

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21955412.svg)](https://doi.org/10.5281/zenodo.21955412)

The survival/extinction theory imported by the theorem layer is proved in
*Contact processes on ballistic Poisson particles*
(concept [DOI 10.5281/zenodo.21955412](https://doi.org/10.5281/zenodo.21955412),
resolving to the latest version — current: v2, arXiv-ready with
self-contained appendices, [10.5281/zenodo.21979354](https://doi.org/10.5281/zenodo.21979354);
v1: [10.5281/zenodo.21955413](https://doi.org/10.5281/zenodo.21955413);
repository: [wake-ballistic-contact](https://github.com/yukie-lab/wake-ballistic-contact)).

## License

- Record (paper, data, figures): **CC BY 4.0**
- Code (this repository): **MIT** (see `LICENSE`)

## AI disclosure

All computations and drafts were executed by an AI system (Claude Code,
model Claude Fable 5) under the direction and arbitration of the human
author, within a written project constitution; see paper Appendix B. The
internal verification protocol is not a substitute for human peer review.

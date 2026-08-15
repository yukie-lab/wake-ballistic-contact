# Contact processes on ballistic Poisson particles

**Criticality, fronts, and when motion helps colonization**

Yukie Maeda ([ORCID 0009-0005-3401-9230](https://orcid.org/0009-0005-3401-9230))

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21955413.svg)](https://doi.org/10.5281/zenodo.21955413)

We introduce a contact process on particles moving ballistically in R³
(Poisson points with i.i.d. velocities; entry-driven fire-and-forget
transmission at range R, pair-once, Exp(T_s) lifetimes, re-marking allowed)
and establish its critical structure: a spectral extinction theorem (A); the
failure of the branching-type bound under re-marking via a certified 4.4σ
"reverse channel" (§4); the static-limit equivalence with bond-diluted
random geometric graph percolation (B); a survival theorem for the full
model proved by a cell–relay renormalization with machine-certified
geometry (C2); the consequence that sufficiently fast motion enables
colonization at densities where static geometry forbids it (D); and a
superlinear/linear front dichotomy (C6a/C6b′). Numerically, whether motion
helps at all is shown to depend on the transmission convention. Full
preprint (with the complete verification disclosure): see the DOI above.

## Reproduce

```bash
python3 src/wake_r/geo_verify.py            # machine certification (geometry + normalization bridge)
python3 src/wake_r/paper_figs.py            # regenerate the three paper figures
python3 scripts/verify_refs.py docs/phase-r/paper/refs.bib   # bibliography resolution check
```

All three are deterministic; the certification uses interval arithmetic and
standard library only. Experiment archives are in `data/phase_r/`.

## Repository map

| Path | Role |
|---|---|
| `src/wake_r/`, `scripts/`, `docs/phase-r/` | **This paper**: falsification device, certifying verifier, figure/citation scripts, proof records, review ledger, paper sources |
| `src/wake_engine/`, `src/wake_data/`, `src/wake_epicyclic/`, `src/wake_g3/`, `src/wake_p2/`, `docs/phase0..2/` | Companion work: arrival statistics on the real stellar catalog (**paper in preparation**) |

## License

The Zenodo record (paper + bundled archive) is **CC BY 4.0**; code files in
this repository are additionally licensed under **MIT** — see [LICENSE](LICENSE).

Release [`v1.0-zenodo`](https://github.com/yukie-lab/wake-ballistic-contact/releases/tag/v1.0-zenodo)
corresponds exactly to the Zenodo v1 deposit (identical `wake-repo-v1.tar.gz`,
sha256 `8c1bfca5114c98a0a751ab695569e9583694833998fde407f73a61307371b8fa`).

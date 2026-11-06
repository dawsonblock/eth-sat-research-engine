# SUPERSEDED — snapshot from before the paper-source pin

This bundle records a snapshot of the working tree whose project manifest had
**664** tests. The current snapshot has **911** tests and 506 manifested
files, and it vendors the paper source in `VERITAS_ETH_v3.8.2/paper/` with a
conformance suite (`tests/test_openai_paper_conformance.py`) that checks every
schedule, packing, Hermite, mode, and count-recovery parameter against the
paper's closed forms.

Still valid here: the qualitative finite-experiment outcomes (dense
reconstruction values, the rejected one-eighth child invariant, the
two-wire/two-level success and the inconclusive four-wire attempt, and the
symbolic Cauchy checks). The *counts* — test totals, manifested files, work
ledgers, and elapsed/RSS figures — belong to the old snapshot.

Before citing anything from this directory, regenerate it against the current
tree and re-run `scripts/build_release.py` last so the manifest matches.

Current statements live in `VERITAS_ETH_v3.8.2/docs/OPENAI_PAPER_CONFORMANCE.md`
and `VERITAS_ETH_v3.8.2/docs/FINITE_V39_AUDIT_REPRODUCIBILITY.md`.

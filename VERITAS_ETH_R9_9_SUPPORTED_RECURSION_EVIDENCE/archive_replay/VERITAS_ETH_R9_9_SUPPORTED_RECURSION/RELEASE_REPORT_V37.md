# VERITAS-ETH v3.7.0 — Finite D.4.4 child-tensor reference report

## Implementation

Built from the cumulative v3.6.0 source. Added an exact group-local packet tensor evaluator consistent with the child-network definition in manuscript Appendix D.4.4. For each fixed beta, the new packet tensor extracts target-mode coefficients and substitutes source-mode linear forms; mode exponents are metadata, not child graph edges. Original half-ports are the only child wires.

## Validation run

- 56 targeted automated tests passed (v3.0–v3.7 related modules), using the archived project with `PYTHONPATH=src`.
- 40 additional seeded exact modular comparisons passed against independently evaluated Cauchy half-edge contractions.
- CLI construct/check round trip passed.
- Adversarial certificate tampering of result, child-wire count, exponent count and claim status was rejected.
- SHA-256 file manifest verified and ZIP extraction integrity checked.

## Explicit unresolved requirements

This is a finite oracle/reference solution to the *packet child definition*, **not** the manuscript's entire recursive algorithm. The oracle still enumerates group-local assignments. `r=2` scaled examples do not meet the full `r=64` packing hypotheses or demonstrate universal `M/8`. The full source-pinned proof correspondence, tapered-Hermite precision scheduler, recursive child invocation, polynomial space and subexponential complexity are all unverified here. The complete inherited regression suite was not rerun as part of this release; only the 56 targeted tests and the seeded suite were executed.

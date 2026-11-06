# VERITAS-ETH v2.1.0 — release report

## What is new

- Admissible-lower-bound exact branch-and-bound for finite packet partitions
  of sizes 1, 2, 4 and 8; bounded by default to 24 wires.
- Independent incidence-score and bound checker; small exhaustive subset-DP
  oracle cross-check, interrupted-search gap and explicit evidence states.
- Updated API, CLI and browser operation without removing v2.0 features.
- Seeded differential, cutoff, tampering and count-preserving relabel tests.

## Scope restrictions

This is a finite proxy optimizer only. It does not implement the paper's
D.3 packing theorem or D.4.4 subexponential recursion. Larger-instance
optimality is an internal completed-enumeration claim, not an independent
cryptographic proof certificate. Small independent DP comparisons are
explicitly labeled separately. A terminated search returns a feasible
incumbent, never an unearned optimality declaration.

## Validation

See `validation/validation_v21.json` and `validation/benchmark_v21.json`
for measured results. No generalized speedup is claimed.

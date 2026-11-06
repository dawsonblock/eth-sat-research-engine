# VERITAS-ETH v2.2.0 — release audit

## Delivered

- Cumulative upgrade from the existing v2.1.0 source archive.
- New proof-carrying component-DAG #SAT generator and structural checker.
- Free-variable multiplicity, deterministic unit propagation, disjoint
  component products, exact binary case splits, and canonical state reuse.
- `/v1/certify/count-dag`, `/v1/certificates/check-count-dag`, CLI `--certify-count-dag`,
  `check-count-dag`, and a browser-console operation.
- New tests, seeded differential validation, and reproducible benchmark.

## Verification ledger

- Full inherited pytest suite: see command transcript in `validation/release_summary_v22.json`.
- New `scripts/validate_v22.py`: 2,000 seeded CNFs; each DAG count agrees with
  independent exhaustive enumeration, and altered root-count claims are rejected.
- Inherited `scripts/validate_10000.py`: 10,000 SAT/#SAT regression inputs.
- `benchmarks/v22_count_dag.py`: proof-checks both methods on four bounded examples;
  12-disjoint-OR instance: tree 12,286 nodes / 493,161 JSON bytes; DAG 39
  nodes / 2,314 JSON bytes. Actual wall times are workload-dependent and
  recorded in the benchmark JSON.
- Startup smoke, CLI sample, archive extraction, manifest verification and
  ZIP integrity are release requirements.

## What this does not demonstrate

This is not an implementation of the ETH paper's D.3 collision-packing
construction, specialized D.4.4 low-rank mode recurrence, or its asymptotic
subexponential-time algorithm. It is exact, auditable and useful on some
structured inputs; worst-case complexity remains exponential. Lean proof
reproduction is not part of this package's validation.

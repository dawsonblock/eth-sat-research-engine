# VERITAS-ETH v1.6.0 — final build and validation report

## Added

1. An exact indexed factor-elimination backend using compiled local bit projections, capped per-bucket scratch space and fallback projection extraction.
2. A separately selectable exact nonzero-only sparse factor hash-join backend. Its `peak_table_entries` is a count of stored nonzero rows, not the size of an equivalent dense factor.
3. A quick-first original-CNF minimum-degree plan with automatic fallback to the prior three-heuristic / two-representation portfolio when it does not fit budgets. The user can request the thorough portfolio.
4. Faster separator-recursion leaf planning and selectable execution backends; API, CLI, browser labeling, tests, benchmark and documentation updated.

## Tested

- Automated suite: **238 passed**, including new v1.6 tests.
- Additional seeded v1.6 differential validation: **400 input formulas**, **10,000 exact/modular comparison checks**, **zero mismatches**.
- Inherited 10,000-instance SAT/#SAT validation passed, 106 tensor checks passed.
- Inherited 800-case COPY3 validation passed.
- Startup smoke and new CLI/API parameter checks passed.
- Five structured benchmark cases: all strategies returned identical counts; see `validation/benchmark_v16.json`.

## Benchmark interpretation

The release microbenchmark compares four execution configurations *within v1.6.0*: `v16_thorough_legacy`, `v16_fast_indexed`, `v16_full_indexed`, `v16_fast_sparse`, with four executions for each input. It does **not** purport to be an unmodified v1.5.0 binary versus v1.6.0 comparison. The small, structured cases are not representative of SAT hardness, results depend on the runtime and hardware, and the fast-first plan may select inferior orderings for some inputs. The sparse backend may be slower than indexed on dense workloads.

## Explicit nonclaims

All added algorithms are conventional exponential-worst-case exact contraction methods. There is **no** verified implementation of the manuscript's D.3 packing lemma, D.4.4 weighted-mode count theorem, subexponential recursive algorithm, or a verified time-complexity improvement. These validation tests do not certify the upstream Lean proof. Resource limits are algorithmic, not operating-system memory isolation.

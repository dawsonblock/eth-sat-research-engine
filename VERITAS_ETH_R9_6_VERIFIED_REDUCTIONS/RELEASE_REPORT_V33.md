# VERITAS-ETH v3.3.0 verification report

## New implementation

Exact sparse recursive mode-exponent contraction with components, conditioned separator branching, memoization and fail-closed time/work/cache/depth limits. Independent checks compare the recursive result against v3.2 sparse elimination and direct Cauchy half-edge enumeration. Full source replay is required for accepted certificates.

## Verified in the current build

- `tests/test_v33_recursive_bonds.py`: 6 passed, including 100 independent random sparse-factor brute-force tests inside the suite, tamper detection, budget enforcement, component factorization, cache reuse and API/CLI execution.
- `scripts/validate_v33.py`: 45 seeded finite Cauchy triple-oracle comparisons passed.
- Selected cumulative suite covering v2.6/v2.9/v3.0/v3.1/v3.2/v3.3 and exact counting: 77 tests passed.
- `scripts/smoke.py`: passed.
- `scripts/validate_10000.py`: 10,000 SAT/counting differential instances passed and 106 tensor reference checks passed.
- Entire cumulative `pytest -q` run: reached approximately 80% without a reported failure, then exceeded execution limit. FULL SUITE NOT VERIFIED IN THIS RUN; it has 451 collected tests.

All source files are included in the release manifest, and the packed release was extracted and its digests and new tests checked.

## Limitations

This implementation remains a small finite exact reference. There is **no** manuscript-specific recursively shrinking D.4.4 packet tensor construction, verified M/8 child-size reduction, polynomial-space proof or subexponential time proof. The recursion may be exponential and can exceed declared limits.

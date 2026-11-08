# v1.6.0 exact contraction optimization

Validated 238 automated tests; 400 seeded formulas and 10,000 new differential checks. See `RELEASE_REPORT_V16.md`.

Indexed bit-projection executor, separately selectable exact sparse hash-join backend, quick min-degree planner fallback, API and CLI controls, comparative validation and benchmark. No proof of ETH runtime or unconditional speedup is claimed. See `docs/FAST_SPARSE_CONTRACTION_V16.md` and `validation/benchmark_v16.json`.

---

# VERITAS-ETH v1.5.0 release verification

Cumulative source based on verified v1.4.0 archive; all earlier modules retained.

## Completed validation (this build)

- `pytest -o addopts='' -q`: **234 passed**.
- `scripts/validate_v15.py`: **500 random instances**, **4,500 differential exact/modular comparisons** passed.
- `scripts/validate_10000.py`: **10,000** reference-versus-exhaustive SAT/#SAT comparisons passed; plus **106** bounded tensor checks.
- `scripts/validate_v14.py`: **800** old COPY3 random comparisons passed.
- `scripts/smoke.py`: passed.
- Side-by-side v1.5 vs v1.4 benchmark: all **4 exact counts agreed**.

## Observed performance

All four initial small/structured benchmarks showed **more wall-clock overhead for v1.5** than v1.4, despite fewer estimated assignment evaluations. These measurements are single-run, platform-dependent and include planning. See `validation/benchmark_v15.json` for all counts and times. This release should not be described as a demonstrated general speed improvement.

## Mathematical scope and claims excluded

The new planner, separator DP and slicing are exact for their supported inputs and subject to resource/time limits, but still have exponential worst-case complexity. No ETH subexponential algorithm, D.4.4 theorem reproduction, asymptotic complexity proof or independent Lean proof rebuild is claimed. Passing finite-instance checks is not a mathematical proof of the manuscript's bound.

Manifest and archive-integrity checks are run after packaging; see `SHA256SUMS.txt`.

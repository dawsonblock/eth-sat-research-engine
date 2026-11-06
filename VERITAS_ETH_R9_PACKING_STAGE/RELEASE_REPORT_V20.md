# VERITAS-ETH v2.0.0 — Release report

**Baseline:** v1.9.0 complete source package, preserved cumulatively.

## Primary change

A global minimum-weight perfect matching optimizer solves the **pair-packet** (`packet_size=2`) version of the finite incidence-collision score. This has a polynomial-time algorithm and does not require the 16-wire exponential subset-DP. It handles odd numbers of wires with a zero-weight dummy and reports separate statuses for independently DP-cross-checked small instances versus larger instances relying on the external Blossom implementation. All non-matching packet optimizers remain available.

## Implementation

- Exact score reduction: `research/matching_packets.py`.
- Independent schedule/score checker: `research/matching_checker.py`.
- API optimizer `matching`, CLI `--matching-packets`, Cauchy `--packet-optimizer matching`, browser selection.
- Optional NetworkX v3.2+ dependency installed by bundled Windows/Linux startup scripts.
- API default wire cap 128; Python cap 128, optionally raised to 256. Pair packets only.

## Validation summary

- 265 tests from the cumulative automated suite passed.
- v2.0 deterministic random validator: 250 comparisons against exact subset-DP plus relabeled exact count.
- 10,000 inherited randomized SAT/#SAT reference checks passed.
- Existing v1.9 large packet checker and legacy API regression passed.
- Startup smoke suite passed.
- Benchmark: `validation/benchmark_v20.json` reports **planning times and finite packet scores only**; no end-to-end SAT/counting speedup has been demonstrated. On easy cyclic inputs the heuristic commonly matches the global optimum faster.
- ZIP integrity and extracted-file checks are performed after packaging.

## What this does NOT establish

This does not reproduce the manuscript's D.3 quantitative collision packing theorem, D.4.4 mode counting, or claimed subexponential tensor recursion. The finite surrogate is not known to predict exact Cauchy polynomial execution time. On >16 wires, the checker verifies the matching and score but **not** a standalone optimum proof certificate; the global optimality assertion depends on the correctness of NetworkX's Blossom solver. The external matching routine cannot be forcibly interrupted by the API request's `timeout_s`; use process isolation for hard deadlines.

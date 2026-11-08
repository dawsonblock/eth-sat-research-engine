# VERITAS-ETH v1.9.0 — Release report

## Changes shipped

**Full cumulative v1.8 source preserved.** New `research/scalable_packets.py`
performs deterministic, seeded, bounded multistart packet planning on larger
networks (default cap 256 wires; public API caps 128 wires). It uses
pair-incidence weights and incremental cross-packet score updates. Schedules
are always replayed using the original factor-incidence implementation.

**Independent mathematical check:** `research/packet_bound_checker.py` verifies
the exact achieved score and lower bounds with its own factor-incidence loops
and a distinct balanced-bin bound construction. It rejects altered scores,
permutations and false exactness claims. A returned optimum is *certified only
for the finite surrogate score* when `(achieved_pairs, achieved_peak)` equals
the provable componentwise lower bounds. Otherwise the output is an explicitly
uncertified feasible schedule. See `docs/SCALABLE_PACKET_BOUNDS_V19.md`.

The new scheduler is selectable via CLI, FastAPI, browser operation and the
optional bounded Cauchy polynomial elimination path. Existing `legacy` and
`exact_dp` paths are retained.

## Validation actually run in this environment

- Full regression suite: **257 automated tests passed**; see `validation/release_summary_v19.json`.
- `scripts/validate_v19.py`: **496** global-score bound comparisons against
  independent permutation enumeration; **489** schedules attained the lower
  bound and were soundly certified; **7** did not reach it and were not
  falsely marked optimal; **124** small original-count relabeling comparisons.
- Eight larger, seeded packet-search cases (64–120 wires) all passed
  independent bound verification; several exceeded the evaluation budget and
  properly retained uncertified feasible schedules.
- `scripts/validate_10000.py`: **10,000** reference SAT/count versus
  exhaustive cases passed; **106** tensor comparisons passed.
- `scripts/smoke.py`: passed.
- v1.9 unit tests include deliberate forged-evidence rejection, seeded
  determinism, resource caps, API/CLI compatibility and small Cauchy-jet
  agreement after relabeling.
- Benchmark `benchmarks/v19_packet_search.py`: six sizes 16–128 wires.
  Planner timings are single-run observations, not representative end-to-end
  SAT performance metrics. Some specially structured cases reached zero
  collisions; no SAT runtime speedup is inferred.

## Remaining research limitations

The v1.9 bounded incidence objective is NOT the manuscript's D.3 quantitative
packing property. The D.4.4 specialized weighted-mode recurrence and its
subexponential complexity analysis are NOT implemented. This remains a
conventional exact, worst-case-exponential mathematical research system.
The optimizer's memory limits are logical caps, not OS-level hard sandboxing.

# R9.11 — portable finite replay, generalization still partial

Baseline: R9.10 commit `6872f0a`, preserved unchanged. Branch:
`r9.11-portability-and-coupled-recursion`.

Implementation source SHA-256:
`925b1196f1b5ee1363a97810ef0fca8bbb561a36ffac2c41800a08e236f96702`.
The inherited distribution version remains `3.8.2.post98`; source hashes and
archive manifests identify this revision. The R9.10 and R9.9 checkouts and both
sealed R9.10 ZIPs remain unchanged.

## Portability defect fixed

The independent mode and interpolation oracles now accept validated finite
work/time policies. R9.11 defaults retain the 5,000,000 per-invocation work cap
and align the oracle time cap with the overall time allowance. The CLI exposes
`--oracle-max-work` and `--oracle-max-seconds`.

The interpolation timer includes child computation between interpolation
operations. The earlier implicit 60-second cap was therefore not an exclusive
arithmetic timer. Receipts now document that clock scope and the exceeded
resource. Resource exhaustion returns `INCONCLUSIVE_RESOURCE_LIMIT`, never a
partial answer or a successful skipped check. Numerical inconsistencies still
return invalid evidence. Limits are cooperative; observed time can exceed a
limit before the next check.

A narrowly pinned R9.10 schema compatibility path preserves the historical
producer digest while separately recording the new checker digest. Unknown
source digests remain refused. Every mathematical dependency is still replayed.
This is unsigned provenance consistency, not author authentication.

| Sealed R9.10 certificate | New independent replay | Point checks | Checker work units | Observed seconds |
|---|---|---:|---:|---:|
| 235 wires, `31 * 2**234` | PASS | 140 | 7,644,272 | 60.78 |
| 242 wires, `17 * 2**241` | PASS | 140 | 6,364,001 | 49.20 |

Both used 5,000,000 work units per oracle invocation and a 600-second time cap.
Their original report and event bytes were not modified. Fresh R9.11 production
of the 235-wire example also passed independent replay and the exact matching
reference. Deliberate one-work-unit and one-second oracle probes returned
inconclusive resource statuses with no result and identified the respective
work/time limit. Deterministic fault tests cover both paths, source compatibility,
unknown source rejection, and failure of a required verification step.

## Coupled arithmetic: one level passes; two levels remain inconclusive

The new cycle fixture uses multi-port rank-two matrices and a separate integer
transfer-matrix reference, tested against exhaustive enumeration on small
asymmetric-table cycles. No reference value enters recursive execution.

The completed 44-wire cycle has two adjacent nonconstant row tensors, all 22
column tensors nonconstant, and 20 constant row tensors. It is connected and has
a coupled core, but still has constant-row padding and bounded graph width.
Its exact contraction is **302982134081445662325614**.

| 44-wire one-level run | Cache enabled | Cache disabled |
|---|---:|---:|
| Computations | 222 | 6,273 |
| Cache reuses | 6,051 | 0 |
| Evaluated points | 26 | 26 |
| Tuple contributions | 98 | 98 |
| Child transitions | 6,272 | 6,272 |
| Producer charged work units | 7,302,996 | 27,794,650 |
| Independent replay and integer reference | PASS | PASS |

These are deterministic finite work-policy comparisons, not bit-operation or
wall-speed claims. Timing/RSS measurements were collected on a shared host with
concurrent validation jobs.

The 484→44→4 coupled-core experiment did **not** complete. Its first attempt
reached the inherited 20 MB logical certificate limit after 15 point evaluations;
about 98% of written bytes were point records. With a 100 MB certificate allowance
and a 180-second overall budget it reached 33 point evaluations, then refused
at the next time check (185.80 seconds). Neither attempt returned an answer.

A fully nonconstant 484-wire cycle, with every vertex matrix rank two, exhausted
a separate one-million-work budget during Hermite planning before any point
evaluation. Its transfer reference is separately recorded; that reference is not
a recursive result. Consequently, the connected two-active-level acceptance gate
remains open. Increasing edge counts or completing the one-level example does
not close it.

## Row-density sweep

The bounded sweep varies nonconstant matching-row ports through
`1, 2, 4, 8, 16, 32, 242`, fixing 242 wires and 1,024 coefficient bits. The root
sample bounds are `8, 14, 26, 50, 98, 194, 1454`.

Initial default same-group layouts produced inadmissible next-level vertices;
those refusals are retained. The corrected sweep uses the shifted root layout
from the matching construction. Each attempt has a 12-million-work / 120-second
policy. All seven shifted-layout attempts exhausted their resource policy,
without a parent answer. The partial evaluations below span the recursion; none is a completed root grid.

| Nonconstant row ports | Root sample bound | Completed points, all levels | Charged work units |
|---|---:|---:|---:|
| 1 | 8 | 107 | 9,016,966 |
| 2 | 14 | 84 | 10,846,408 |
| 4 | 26 | 35 | 6,520,254 |
| 8 | 50 | 51 | 5,407,005 |
| 16 | 98 | 53 | 4,315,076 |
| 32 | 194 | 43 | 4,215,280 |
| 242 | 1454 | 22 | 5,726,730 |

Incomplete runs are not compared as if
they solved equal amounts of work. See `experiment_summary.json` in the evidence
archive for each refusal, partial work, point count, event footprint and policy.
The field degree varies with the required interpolation capacity and is recorded
in every input.

The largest recorded coupled-core point duplicated its complete local-coefficient
array in the original and folded data. Its 44 port-identified entries also shared
one identical coefficient value. `point_payload_profile.json` records the exact
sizes. Removing this duplication is a concrete next serialization target; it is
not an implemented optimization or a complexity result.

## Validation and remaining gates

The C++ self-test, 13 inherited commands including the 41-module Lean gate, and
all 35 primary clean-wheel/Docker commands passed. Two additional portable
replays of the new connected one-level certificate also passed. The full suite
passed 1,990 tests, with 2 optional pybind tests skipped. Both sealed certificates replayed in
each portable environment. The exact commands and results are recorded in the accompanying
evidence summary. Lean model compilation does not establish refinement of the
Python executable. The first candidate failed an unchanged legacy budget-exception
test. The correction preserves the enclosing budget's exception type and adds
work/time regression tests; the final source was revalidated from scratch. The
failed-candidate logs remain separately identified in the evidence archive.

| Gate | Scope of this revision |
|---|---|
| Certificate portability | Fixed; both historical certificates fully replayed |
| Connected two-active-level contraction | INCONCLUSIVE_RESOURCE_LIMIT |
| Manuscript-active schedule, higher valuations and arbitrary jet length | Not implemented in this recursive executor |
| Cost accounting | Finite charged work, event bytes and process RSS only |
| General time/space bounds and Python-to-Lean refinement | Not established |
| General CNF integration, competitive solver benchmarks and resumability | Not extended here |

`bit_operations` remains null. A failed run's ledger can exclude pending oracle
charges, which are separately reported when available. Per-call accounting lists,
cache object overhead and streamed certificate storage still need a general space
argument. Source qualification and theorem mode remain disabled.

Reproduction commands, clock semantics and fixture restrictions are in
[the technical notes](docs/R911_PORTABILITY_AND_GENERALIZATION.md).

# R9.11: certificate portability and bounded generalization experiments

R9.11 fixes a finite replay resource defect. It does not implement the manuscript-active schedule, arbitrary jet length, a general complexity bound, or Python-to-Lean refinement. The executable continues to use finite `a=u=1`, `ell=1` recursion. Source-qualified theorem mode remains disabled.

## Replay policy

The independent Cauchy/mode and interpolation meters accept an explicit `OracleLimits(max_work, max_seconds)` policy. The validated ranges are integer work limits from 1 through 1,000,000,000 and integer time limits from 1 through 3,600 seconds. These are finite engineering caps, not mathematical complexity bounds.

The R9.10 CLI now accepts:

- `--oracle-max-work` (default 5,000,000 per invocation).
- `--oracle-max-seconds` (default the overall `--max-seconds`).

Each meter is capped by the remaining overall budget. The interpolation meter measures its entire lifetime, **including recursive child computation between interpolation operations**. It is not an exclusive CPU timer. The former implicit 60-second limit could therefore fail a required parent interpolation check after successful child computation. No check is bypassed by the new policy.

`OracleBudgetExceeded` and independent reference arithmetic exhaustion return `INCONCLUSIVE_RESOURCE_LIMIT`. Work and time failures identify the stage, limit, observed usage and limit scope in `resource_failure`. The result field is absent. Other structural resource refusals can still have a null `resource_failure`; their explicit reason is retained. Invalid equations, altered contributions, unknown source digests and malformed streams remain invalid evidence. Limits are cooperative checks, not operating-system-enforced deadlines or memory bounds. On a refusal, the ledger contains work charged so far; an interrupted oracle can also have pending work reported in `resource_failure`. Do not interpret that partial ledger as a complete count of all executed arithmetic.

Historical callers without an explicit oracle policy retain the old per-invocation defaults. The R9.11 policy is passed through both producer-side cross-checks and independent replay.

## Certificate identity

The checker accepts its current source digest or the explicitly pinned R9.10 producer digest:

`b27dc09a233e843d933e329d84df92f3bb94284f7767efff68782a93666e22da`

This exception is restricted to the existing `VERITAS_R910_NUMERICAL_V1` schema and all its numerical checks. A receipt records `producer_source_sha256`, `checker_source_sha256`, and `source_compatibility`. The original report and event stream are never rewritten to pretend they were produced by the new source. The checker also checks its own source identity again before returning success.

Digest agreement is provenance consistency, not author authentication. Numerical validity still requires every child, supported tuple, point accumulation, Hermite reconstruction and final result to be independently checked.

## Reproduce the sealed replays

From this checkout, with R9.10 evidence available as a sibling directory:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli \
  examples/r910_matching235.json \
  --layout-file examples/r910_matching235_layout.json \
  --replay-dir ../VERITAS_ETH_R9_10_EVIDENCE/final/numerical/run \
  --output-dir /tmp/veritas-r911-replay235 \
  --max-seconds 600 --oracle-max-seconds 600 --oracle-max-work 5000000

PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli \
  examples/r99_nonconstant_matching242.json \
  --layout-file examples/r99_nonconstant_matching242_layout.json \
  --replay-dir ../VERITAS_ETH_R9_10_EVIDENCE/final/numerical242 \
  --output-dir /tmp/veritas-r911-replay242 \
  --max-seconds 600 --oracle-max-seconds 600 --oracle-max-work 5000000
```

Output directories must not already exist. A deliberate `--oracle-max-work 1` refusal is a resource test, not successful verification. The Python distribution retains its inherited version string; use the source digest, not that string, to identify this revision.

## Connected-core experiment

`scripts/experiment_r911.py` constructs a 484-wire bipartite cycle. Two adjacent row tensors and their connecting column tensor have rank-two 2-by-2 matrices. Their entries cannot be written as independent unary factors. Remaining constant tensors are explicitly reported as padding. `--all-columns` makes every column matrix rank two but still leaves constant rows. Even a fully nonconstant cycle has bounded graph width; this experiment is not a hard general-contraction benchmark.

A shifted root layout yields 44-wire descendants. Component-preserving descendant packing yields four-wire leaves. Actual construction and checking still enforce all per-call packing and shrink conditions. The driver does not replace a child contraction with a reference value.

The separate reference computes the trace of a product of integer 2-by-2 matrices. Small asymmetric-table cycles are also checked by literal exhaustive enumeration. Reference answers are written separately and never fed into recursive execution.

```sh
PYTHONPATH=src python3 scripts/experiment_r911.py \
  --output-dir /tmp/veritas-r911-cycle \
  --active-rows 2 --max-seconds 180 --max-work 12000000 \
  --max-certificate-bytes 100000000
```

A completed two-level run requires a full independent replay, a nonconstant active descendant, and agreement with the integer reference. `--cycle-pairs 22 --all-columns` selects a separate 44-wire one-level check; its success status explicitly says one level. A resource refusal leaves the generalization gate open. In particular, a large connected graph with a small coupled core does not establish performance on networks with many interacting nonconstant tensors.

## Row-density sweep

The matching experiment fixes 242 wires and 1,024 coefficient bits. It varies the number `b` of nonconstant rows, whose tables are `[1,3]`; their columns are `[2,5]`. All other tensors are `[1,1]`. Its independent integer reference is `17**b * 2**(242-b)`, with modular reduction recorded explicitly. The root degree certificate gives `2*(3*b+1)` samples. This formula is a schedule bound, not a runtime bound.

```sh
PYTHONPATH=src python3 scripts/experiment_r911.py \
  --kind matching --active-rows 4 \
  --output-dir /tmp/veritas-r911-b4 \
  --max-seconds 120 --max-work 12000000
```

Use `b=1,2,4,8,16,32,242`. A shifted root layout prevents both halves of a matching edge from creating an inadmissible degree-two descendant at the next capacity-one level. The initial unshifted attempts are retained as layout refusals, not hidden or counted as numerical results.

The reports expose actual work units, points, calls, transitions, cache behavior and process RSS. Bit-operation counts remain null. Working memory, retained accounting lists, cache overhead, certificate size and output storage still require a separate general space argument. Measurements collected alongside validation jobs are shared-host observations, not controlled performance comparisons.

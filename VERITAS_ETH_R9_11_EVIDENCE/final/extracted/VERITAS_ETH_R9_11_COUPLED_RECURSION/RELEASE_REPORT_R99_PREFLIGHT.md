# R9.9 finite preflight and execution admission release

This is a development checkpoint of the accepted staged plan. The source
recurrence and its universal proof are not completed by this release.
The previous supported-recursion worktree and archive remain unchanged.

## Implemented

- Immutable explicit execution choices for schedule, tuple strategy, recovery
  and leaves; incompatible source/finite combinations are rejected.
- Manuscript conformance ledger bound to four file hashes and exact statement
  hashes, with checker scope and outstanding obligations for each component.
- Independent occupied-slot child topology projection and actual port replay,
  including X/Y distinction, inherited order, packet identity and precision.
- Admission before expensive point modes or Hermite weights: actual shrink,
  descendant feasibility, complete grids, field size, precision and call
  lower bounds. Preflight work is charged to the total production budget.
- Finite group comparison using actual singleton descendants. Root weighted
  counts are exact without enumerating their tuples; no modes are discarded.
- Certified constant-row cancellation in the full-tapered supported path.
  This simplifies the point sum while retaining the complete grid and the
  original tapered functional.
- External preflight CLI with optional independently checked point counts.

See [mathematics, CLI and remaining implementation](docs/R99_MANUSCRIPT_PREFLIGHT.md).

## Validation

| Gate | Fresh result |
|---|---|
| Python suite | 1913 passed, 2 optional pybind skips, zero failures/errors |
| C++ Release build and selftest | PASS |
| Inherited/component commands | 13 passed |
| Existing Lean model and axiom gate | 41 modules passed |
| Clean wheel and Docker commands | 26 passed |
| New full-tapered cancellation case | 134 points, 8,577 calls; every point independently checked |
| Fresh actual two-level recurrence | 242 -> 22 -> 2 edges; 56,449 calls; independent recursive replay passed |
| Fresh root Cauchy formula | All eight matching-root points checked independently |

The 242-edge regression uses the separate degree-certified Taylor path. It
is not the combined connected, multislot, exponent-two, two-active-level,
full-tapered acceptance case. That combined case remains NOT_RUN_RESOURCE_GAP.
Full container pytest and hosted CI were not run.

## Mathematical blockers

With 64 groups, four-edge leaves and full-grid recomputation, any successful
run with two active levels needs at least 12,199,681 calls. The current hard
policy limit is 2,000,000. Actual supplied layouts give larger lower bounds.

For the 484-edge cycle, 512 groups reach four-edge leaves immediately. A full
grid nevertheless requires at least 1,487,873 calls before extra tuples;
the complete root weighted tuple count at a nonzero point has 616 decimal
digits. The grid needs field degree at least 11 and its raw coordinate payload
at that degree is 125,818,176 bytes before object or JSON overhead. Raising
fan-out alone does not solve these costs.

Next work is lazy mode construction with certified aggregation, streamed
full-tapered recursive evidence and replay, measured interpolation costs,
recursive jet support, source-compliant packing and formal correspondence.
No large resource-gap run was launched, and no oracle replaced a recursive
production result.

## Identity and evidence

- Baseline commit: `739eb96bd01d1ced559013d0324eadc9b862c4d7`.
- Implementation source digest: `b3c8731f51f5432589a610db4556ce4fe49a58fd759f2e7a0222b64521db4c3f`.
- Manuscript commit: `4eaee87548250b2682affda7d05d947c05554bae`.
- Evidence: sibling `VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_EVIDENCE` directory.
- Consolidated results: `validation_summary.json`; evidence hashes:
  `REVIEW_SHA256.json`; final runs: `full_v2`, `inherited_v2`, `portable_v3`,
  and `final_v2`. Interrupted preliminary checks are retained separately.
- Archive: `VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_VALIDATED_FINITE.zip`.

`source_qualified`, `theorem_mode_enabled`, and universal Python refinement
remain false. Bit-time and peak-space bounds remain COMPLEXITY_NOT_ESTABLISHED.
The existing Lean results have their recorded premises; they do not prove
universal Python execution. Host budget counters are cooperative and do not
establish a hard operating-system memory bound.

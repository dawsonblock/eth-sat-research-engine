# R9.9 two-level streaming layout connection

Implementation source SHA-256: `b2a6f9876525e61080374c8b2693787a5cd88430c2c7a0b42a489dc20ff4e9fa`.
The sealed streaming-resources baseline is preserved in its separate checkout.

## Delivered behavior

The external streaming CLI accepts `--layout-file`, authenticates its original
parent digest, enlarges the scalar root field when necessary, and independently
re-audits the layout bound to the prepared parent. It checks descendant topology
using the same singleton first-fit strategy supplied to recursive execution.
Original preflight provenance is retained and the adapted report is rehashed.
`--preflight-only` returns no contraction result and starts no tensor arithmetic.
Preflight work is charged to the subsequent execution budget.

Legacy estimates for recomputing every child and retaining every grid are
preserved as advisories for the cached streaming executor. Other structural
and precision blockers remain admission failures. Runtime feasibility is not
inferred from topology admission; execution still enforces its resource caps.

## Fresh results

- Projected two-level matching topology: **242 -> 22 -> 2**, with both active
  levels packable. Degree ten supplies 1,024 residues for the 727-point root grid.
- Actual one-active-level 22-edge matching through the layout-file CLI:
  all 134 grid points, 135 actual computations, 8,442 cache hits, and
  8,576 child transitions. Result `31^22`; independent streamed replay passed.
- The connected 242-edge executor probe returned `INCONCLUSIVE_RESOURCE_LIMIT`
  at Hermite-plan budget admission, with one call and zero evaluated points.
  Its conservative work charge was 33,865,497 against a 1,000,000 cap.
  This is a policy refusal, not measured hardware exhaustion.
- Full pytest: **1933 passed, 2 skipped**; no failures or errors.
  C++ Release build and self-test passed.
- **13 inherited commands** passed, including the 41-module Lean/axiom gate.
- **31 clean-wheel/Docker commands** passed, including installed connection
  tests and explicit installed source identity checks. An initial installation
  was rejected by the identity check and rerun with an explicit wheel reinstall.
  Full container pytest and hosted CI were not run.

## Remaining scope

The 242-edge input is a matching. The successful topology projection is not an
executed two-active-level numerical validation and is not the combined general
connected, multi-slot, nonconstant, exponent-two acceptance case. That full
numerical case remains unestablished. Mode counts, interpolation work and total
recursive work can still exceed budgets. Source packing, source-active execution,
universal executable refinement, and bit-time/peak-space proofs remain open.
The inherited Lean gate does not prove the new Python connection. Theorem mode
and source qualification remain disabled.

See [the external CLI](docs/R99_TWO_LEVEL_CONNECTION.md).
Final evidence is external in
`../VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_EVIDENCE/final/`.
Earlier preliminary evidence is excluded from these release results.

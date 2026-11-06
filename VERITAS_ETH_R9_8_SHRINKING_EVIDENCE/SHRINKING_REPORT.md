# Actual shrinking recursion implementation

Implemented on `dev/r9.8-shrinking-recursion`, commit `fba7ee961fc7d5980a396915b0dae93dda6640e0`.
Source binding: `4dc8b3adffe7d3baf923e8ce37140462b73769913ad4064b7c847d1faf948165`. The previous correction branch and sealed R9.7/R9.8
baselines remain intact; this is a development snapshot, not a new sealed release.

The new `contract_shrinking` constructs actual 64-group packet children, checks
`64*M_child <= 6*M` before any recursive call, independently verifies their
ports and entries, and recursively recomputes all 64 values. Successful leaves
have at most four edges. A requested depth is never used as successful termination.

Both the matching and connected-cycle external CLI cases execute **484 → 44 → 4**.
Each has **5,761 actual calls, 5,760 child transitions, 90 complete point values,
45 recoveries, and zero nonshrinking children**. Each result is `2^484 mod 2^512`.
The test suite also verifies a weighted connected 484-cycle with result
`2^484 * 15^242 mod 2^512`, and a connected 64-cycle with nonconstant column
tables whose result is `17^32`. Maximum working precision is **34,304 bits**.

The packer balances whole vertices on each side, supports connected graphs,
and preserves inherited port order. Independent actual side-load checks imply
the numerical child bound; the constructor separately enforces the resulting
actual wire count. It refuses a layout that cannot meet the load bound.

The recursor currently supports the independently certified **constant-row
deformation family at every active call**. Summing the Boolean row affine
factors proves the deformation has degree zero. Both required odd Hermite
nodes are still computed recursively; higher jet coefficients are certified
exactly zero. This is not generic recovery from two samples. All retained
weighted tuples are processed; zero cross-mode coefficients follow from exact
singleton Cauchy values at those nodes, while cross-group ports remain explicit.

Validation: **1616 passed, 2 optional pybind skips**;
**62 new shrinking tests** included. All **12** validators
passed, including the inherited **41-module Lean gate** with complete standard
axiom reports. Fresh Python 3.10 wheel and Linux Docker checks execute actual
two-level shrinking recursion. Full pytest inside Docker and hosted CI were not run.

The general source-active executor, generic nonconstant-row recursion, universal
executable refinement, and asymptotic bit-time/peak-space bounds remain unfinished.
No source/theorem flag was enabled. The source padded packet bound fails on these
scaled roots and is not claimed. Runtime point/child checks are independent; saved traces
do not yet have a separate standalone replay certificate consumer.

[Mathematics and use](../VERITAS_ETH_R9_8_SHRINKING/docs/R98_ACTUAL_SHRINKING_RECURSION.md)
and [machine-readable evidence](verification.json) describe the exact scope.
`REVIEW_SHA256.json` records unsigned artifact hashes, not authenticated provenance.

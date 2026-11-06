# Partial R9.9 general packet implementation

Commit `f1b82607566e5f4e70dfb094a3e785f704a918e1`, source binding `4411d1fbbf002a86e36ccfadcbb20959dde9e7b398ecdee06e49c4393d6f36e9`.

The new general-packet path retains higher mode exponents, computes complete
weighted tuple counts separately from execution admission, and uses actual
64-child construction. Independent rational mode enumeration, packet recipe
checks and parent coefficient elimination verify bounded instances.

Completed evidence:

- Shared-mode coefficients beta 0, 1 and 2 agree with both the independent
  child/parent checker and separate scalar formulas. The beta-two term is
  `480 W00(T) W20(T)` and is nonzero modulo 2^149.
- A separate multi-slot crossing point evaluated all 11,175 weighted tuples
  and all 64 children per tuple: 715,200 child-leaf calls, 55,273,889 abstract
  work units and about 757 seconds. Its value agrees with independent half-edge
  elimination and a direct scalar rational formula. This is one point identity;
  its children do not satisfy the source 6M/64 shrink bound.
- A nonconstant local multi-slot fixture recovered from all 90 points over six
  Hermite nodes, with valuations zero and one. Its result is 289 mod 32 = 1.
- A separate nonconstant 22-edge matching recovered 31^22 through one active
  shrinking level and 134 points. Contraction-oracle entry points were disabled
  in that production test. No successful two-active-level general run is claimed.
- Final full suite: 1,863 passed, 2 optional skips, zero failures/errors.
  Thirteen inherited/component validation commands and 22 wheel/Docker commands
  passed. The 41 existing Lean modules were checked; no new general-recursion
  Lean theorem or executable refinement was proved. C++ Release selftest passed.
- Both checkout and final archive extraction passed all 1,135 manifest hashes.
  Full-container pytest and hosted CI were not run.

The current driver cannot pass two active levels under its 256-point cap:
a positive active packed child needs at least 22 edges, requiring a parent with
at least 235 edges and at least 706 interpolation points per node. The exact
finite derivation is recorded in `two_level_policy_obstruction.json`.

The crossing coefficient fixture with 106 modes has 345,770,425,887 weighted
tuples. Its full point remains refused rather than silently pruned. The smaller
two-mode point above is a different fixture whose complete stream fits the
explicit call/work/time budgets.

Source-compliant packing correspondence, a fully recovered general crossing
parent, two active general shrinking levels, universal Python refinement,
bit-operation bounds and peak-space bounds remain open. `contract_source`
continues to refuse active source recursion. All source-qualified and theorem
flags remain false. Work units are not bit costs and deadlines are cooperative.
The manuscript was checked from the local pinned bytes; the attempted upstream
raw URL did not resolve, so this run does not independently authenticate an
upstream publication or formal release.

The earlier targeted failure was an incorrect expected fixture value (17^22
instead of 31^22). An earlier full run with that stale collected assertion was
terminated and superseded. Those logs remain preserved. The final complete run
used the corrected test and unchanged package bytes.

See `verification.json`, `components.json`, `general_full_point.json`,
`scalar_coefficient_check.json`, `full_point_scalar_oracle.json`, the three
validation summaries, and `final_release_summary.json` for raw evidence.

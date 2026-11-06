# VERITAS-ETH R9 packing-stage report

## Release statement

Review update: the Lean gate was repaired to enforce its pinned compiler
version, require exact theorem axiom reports, and reject nonstandard axioms.
A three-edge fixture confirms the generated Lean and Python labelings can
differ because their vertex orders differ. These findings do not invalidate
the stated Lean arbitrary-order bound, but Python refinement remains open.
Four central statements now have separately stated Lean type contracts.
The resulting 19-module proof gate passed in 27.61 seconds, and 80 focused
tests passed after the contract module was added. The full suite passed 1,150
tests in 102.56 seconds before that final proof-gate inclusion; it was not
rerun afterward. See `docs/R9_SOURCE_AUDIT.md`.

Source-audit update: 1,134 tests passed after correcting the active-call
qualification and fail-closed wrapper. The 16-module Lean check passed, and
the eight-wire V3 transcript was regenerated and replayed. These are finite
regressions and formal sublemmas, not a completed packing or recursion proof.
See `docs/R9_SOURCE_AUDIT.md` and `validation/r9_source_audit.json`.

Subsequent Lean work adds `proofs/D3SymbolPorts.lean`: for its own generated
labeling, it derives the per-side symbol-port bound from the first two
packing inequalities and degree hypotheses. It also proves the radix-64
half-wire inequality under `M>0`; the port bound also holds for any distinct
covering vertex order. This does not construct packet slots or
children, prove Python refinement, or qualify theorem recursion.
`proofs/D3SlotSplit.lean` additionally proves the local inverse relationship
between a slot bit word and its copy/orientation bit streams; the full
edge-to-packet bijection remains open.
The prior 18-module Lean validator passed in 26.25 seconds without a
`sorryAx` dependency in the printed theorems. The focused packing and source
conformance suite passed 74 tests in 5.39 seconds. Normal and optimized
Python finite packing replays passed in 4.33 and 4.27 seconds respectively.
The 1,134-test full-suite result above predates these proof-only changes; it
was not rerun for this snapshot.

This snapshot advances the R8.2 finite research build with a streaming
conditional-expectation labeling implementation, a separately coded rational
certificate checker, and compiled Lean results for finite averaging and
candidate selection. It does **not**
implement or prove the October 2026 OpenAI theorem. The theorem path remains
fail-closed as `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED` in
`src/veritas/research/tapered_v4/recursor.py`.

The pinned contraction source is
`paper/quantitative-contraction.tex`, SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`; the
full pinned paper tree digest is
`f4a10137d8630cb8ff26d031aca38c23a39db4606a4494ff7e43f59b8c671594`.
Relevant source labels are `app:tensor`, `lem:tensor-packets`,
`eq:tensor-packing-conditions`, `subsec:tensor-children`,
`eq:tensor-recursion-identity`, `lem:tapered-hermite`, and
`subsec:tensor-cost`.

## Changes

- `eth_packing_v26/streaming.py` scans exact candidate scores from the edge
  list without retaining an O(M²) pair table. It supports a bounded finite
  mechanism path and a historically named active-call wrapper that requires
  radix 64 and checks all three inequalities using actual graph degree. It
  does not validate the source size, depth, global degree bound, or schedule.
  The finite implementation caps `a` at 64 before computing large powers or
  packet widths; larger requests return an inconclusive resource status.
- `eth_packing_v26/streaming_check.py` recomputes all candidate scores with
  exact `Fraction` probabilities, then checks the complete trace, average
  identity, canonical minimizers, class padding, packet-address uniqueness,
  and observed port loads.
- `proofs/ConditionalExpectationSelection.lean` proves the finite-list
  selection consequence of an exact average identity. It does not itself
  prove the source score identity.
- `proofs/ConditionalExpectationAverage.lean` now proves the finite
  conditional-expectation average for a coordinate-level model of each
  row/column edge-pair comparison. It derives the constraint count and
  two-sided unknown-comparison bounds, handles exact division of powers, and
  lifts the result over finite pair lists and the diagonal baseline.
- `proofs/ConcreteD3ConditionalExpectation.lean` formalizes the row/column
  endpoint classifier for actual bipartite edge pairs and proves the ordered
  overlap count `<= 2*M*Delta` under the row/column degree bounds.
- `proofs/D3VarianceBound.lean` independently enumerates each pair's distinct
  endpoint labels and proves the exact scaled agreement identity and the
  summed finite pair-marginal bound `D*E[Phi] <= 2*M*Delta*D`. It uses exact
  integer product identities, not modular division. The full global
  product-space expansion and its refinement to the Python candidate score
  are still open. See `docs/CONDITIONAL_EXPECTATION_AVERAGE_LEAN.md`.
- `proofs/D3PotentialIdentity.lean` proves the fixed-label identity between
  squared class loads and ordered equal-signature collisions, including its
  scaled form. It is part of the Lean validator and its SHA-256 is bound into
  the finite packing evidence. This does not close the global conditional
  expectation or Python-refinement bridge.
- `proofs/D3CollisionBridge.lean` expresses both the complete-label potential
  and the initial pair-marginal sum using the diagonal plus twice the
  unordered pairs, and derives the initial marginal bound under the degree
  assumptions. Identifying the executable conditional score with these
  expressions remains open.
- `proofs/D3InitialScore.lean` proves that, for an empty assignment, the
  concrete Lean pair terms and total score equal the independent finite pair
  marginals and second moment. The score inherits the degree bound. This
  module handles only the empty state; Python refinement remains open.
- `proofs/D3CanonicalSequence.lean` defines a first-minimum Lean selector and
  a recursive vertex-labeling run. It proves the first selected score satisfies
  the initial bound and proves full-run monotonicity conditional on explicit
  parent-score, child-score, and readiness hypotheses. Later modules prove
  readiness, the parent equality and child equality for the raw Lean state
  score; equivalence with Python's ordering and state updates remains open.
- `proofs/D3StateInvariants.lean` proves readiness and label validity for a
  distinct vertex list, preservation of unlisted vertices, and assignment of
  every listed vertex. Its final score bound assumes the parent-score and
  child-score equalities; it does not prove those equalities or Python refinement.
- `proofs/D3ParentScoreIndependence.lean` proves that the parent score is
  independent of the unassigned next vertex, defines an unmasked Lean state
  score, and proves the parent-score equality for it. Its final-run bound
  still assumes the child transition equality. Global expectation semantics
  and Python refinement remain open.
- `proofs/D3ChildTransition.lean` proves the child transition equality for
  the Lean classifier and derives the complete canonical Lean run's raw-score
  bound without that hypothesis. This module alone does not establish final
  class-load equivalence, global probability semantics, or Python refinement.
- `proofs/D3RealizedLoads.lean` proves the final Lean state score equals the
  actual directed-class square sum, constructs a distinct list covering all
  edge endpoints, and proves the generated Lean run satisfies
  `D * sum_gamma X_gamma^2 <= M^2 + 2*M*Delta*D` under positive radix and
  degree bounds. Packet and port bounds and Python refinement remain open.
- `proofs/D3ClassAccounting.lean` proves total and squared-load identities
  across all directed classes, including empty ones. `D3VarianceAlgebra.lean`
  establishes the centered bound, `D*X <= 2*M` for each class, and
  `D*H <= 3*M` for the common padded size under the first two source packing
  inequalities. Packet slot construction, port bounds and Python refinement
  are not proved by these results.
- `proofs/D3SelectionBridge.lean` composes the formal concrete-edge average
  with finite minimum selection and proves that some label word does not
  increase the modeled score for one current vertex. It does not establish
  the repeated assignment sequence or executable refinement.
- `lean-toolchain` pins Lean 4.35.0. The existing conditional
  `ConditionalChildShrink.lean` proof also compiles.
- `scripts/validate_r9_streaming_packing.py` writes
  `validation/r9_streaming_packing.json` with finite replay results, source
  bindings, resource caps, and explicit qualification limits.
- `scripts/validate_conditional_expectation_lean.py` compiles the base,
  concrete-edge, pair-marginal, pointwise-potential, one-step selection,
  selection, and child-bound Lean files, checks the central theorem names and rejects a
  `sorryAx` dependency. It records the compiler output and source hashes in
  `validation/r9_conditional_expectation_proof.json`.

## Evidence

The unchanged R8.2 input archive was independently identified by SHA-256
`39276152c9715f634396d7f982e779f034a5eb2632bc2ef3cb3cfb30e44b806f`.
The archive had 558 members; CRCs, traversal paths, duplicate names and
symlink entries passed inspection. All 557 manifested files matched under
normal Python and `python -O`. The original archive was not modified.

On Python 3.12.0, the most recent full-suite run was before adding the
unordered-pair bridge; the focused suite and Lean validator below were rerun
after that addition:

- Previous R9 full repository suite: **1,127 executed, 1,127 passed** in 96.78 seconds.
- Focused packing and manuscript-invariant suite: **47 executed, 47 passed**
  in 4.78 seconds, including `tests/test_d3_conditional_expectation_independent.py`.
- After the padded-load proof addition, 69 focused packing,
  conditional-expectation, and source-conformance tests passed in 5.27 seconds.
- R9 finite construction and independent replay: PASS in 4.332 seconds;
  optimized Python: PASS in 4.415 seconds. Both records have the same source
  digest and semantic results; elapsed time is recorded separately.
- Lean 4.35.0 validator: PASS for sixteen modules, including
  `ConcreteD3ConditionalExpectation.lean`, `D3VarianceBound.lean`,
  `D3PotentialIdentity.lean`, `D3CollisionBridge.lean`, `D3InitialScore.lean`,
  `D3CanonicalSequence.lean`, `D3StateInvariants.lean`,
  `D3ParentScoreIndependence.lean`, `D3ChildTransition.lean`,
  `D3RealizedLoads.lean`, `D3ClassAccounting.lean`, `D3VarianceAlgebra.lean`, and
  `D3SelectionBridge.lean`; all central theorem names are present and no
  `sorryAx` dependency is reported. Current timing is in the evidence JSON.
  The central theorems report only Lean foundation
  axioms (`propext`, `Classical.choice`, `Quot.sound`); `sorryAx` is absent.
  The new theorem bounds the finite pair-marginal second moment after
  subtracting `M^2`. It does not formalize the full global product-labeling
  expansion or prove source correspondence with Python's score routine.
- Existing eight-wire V3 regression: exact residue `((1,0,0,0,0),)`, 12,297
  recursive calls, depth 1, 3,074 retained tuples, and 2,299,570 counted
  work units. Transcript write took 12.82 seconds (observed peak RSS
  120,750,080 bytes); replay took 13.39 seconds (observed peak RSS
  269,828,096 bytes) and returned `FINITE_TRANSCRIPT_REPLAYED` with
  `HASH_MATCH_UNSIGNED`. Point identity coverage remains partial/not checked
  by that transcript.

The R9 independent checker replayed a 128-edge 4-regular bipartite fixture
with radix 2 and dimension 1. Its numeric inequalities hold, and the
independent checker confirmed both packet-count and port-load bounds. The
fixture is not paper-eligible because the paper fixes radix 64. It used
2,754,840 observed work units; the conservative estimate was 3,145,665.
These are operation counters, not bit-work or a runtime proof.

Correction to the previous report: `a=1` is a valid packing-lemma experiment
but cannot be an active exponent in the source schedule. Its smallest positive
value is `a=2`, giving `D_arr=2^24`, `L=4`, `Delta>=8`, and the necessary
lower bound `M>=2^52` from the displayed packing inequalities. The source's
global `Delta` and size/depth schedule can impose much stronger constraints.
The wrapper rejected the eight-edge fixture before running the labeler. No
radix-64, theorem-regime packing certificate was executed in this release.

The V1 streaming and compressed K_N,N certificate schemas overstated active
eligibility based on local inequalities. Their V2 schemas do not assert it;
the checker may replay V1's historical fields but explicitly discards that
claim. See `docs/R9_SOURCE_AUDIT.md` for the source comparison.

The full machine-readable evidence is in
`validation/r9_release_evidence.json`; finite packing fixtures and source
bindings are in `validation/r9_streaming_packing.json`.

The prior R9.1 ZIP contained 580 members, with no duplicate names,
traversal paths, symlinks, or CRC errors. Its 579-entry SHA-256 release
manifest passes under normal and optimized Python. A fresh extraction also
passes both manifest checks, the six-module Lean validator, and the finite
R9 packing/replay script. The archive checksum is recorded in the unsigned
sidecar `VERITAS_ETH_R9_PACKING_STAGE_SHA256.txt` beside the ZIP.

## Gate table

| Gate | Evidence | Status | Remaining risk |
|---|---|---|---|
| G0: identify R8.2 baseline | Expected SHA-256, CRC/path/symlink checks, normal and optimized manifest replay | PASS | The R8.2 full-suite count is retained from its report; R9 full suite was rerun here |
| R9: streaming conditional-expectation executable | Exact finite candidate averaging, Lean pair-marginal bound, separate rational replay, generic-radix numeric-eligible fixture | PASS, finite/formal sublemmas only | Global product-space bridge, Python refinement, packet padding proof and radix-64 eligible run remain open |
| Lean selection consequence | Lean 4.35.0 compile and axiom report | PASS, lemma scope only | Does not connect source probability algebra to Python or prove the complete packing lemma |
| Lean labeling, padded classes, and port counts | `D3VarianceAlgebra.lean`, `D3SymbolPorts.lean`, and dependencies | PASS when the updated Lean gate compiles | Packet construction, actual child networks, Python refinement, and bit-cost proof remain open |
| R10: complete mode expansion and all-node parent-child identity | No new R10 proof or implementation in this stage | BLOCKED / NOT STARTED | Universal mode support, tuple identity, inherited recipes and Hermite precision composition |
| Multilevel recursive execution | Existing theorem branch still returns `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED` | BLOCKED | Termination invariants and all-node contraction are absent |
| R11: complexity and outer reduction | Not implemented in this stage | BLOCKED / NOT STARTED | Complete bit-time, depth-first peak-space proof, sparsification and parity-test reduction |
| Regression and packaging | Current audit: 1,134 tests, 74 optimized focused tests, Lean gate, finite R9 replay and eight-wire V3 write/replay | PASS, finite scope | No hard memory limit, signed build, universal theorem qualification or Python 3.13 run |

## Reproduction commands

Run from the repository root with Python 3.12 and test dependencies installed:

```sh
PYTHONPATH=src python3 -m pytest -o addopts= -q
PYTHONPATH=src python3 -m pytest -o addopts= -q tests/test_d3_streaming_independent.py \
  tests/test_d3_implicit.py tests/manuscript_invariants/test_eth26_d3.py \
  tests/test_d3_conditional_expectation_independent.py
PYTHONPATH=src python scripts/validate_r9_streaming_packing.py
PYTHONPATH=src python3 -O scripts/validate_r9_streaming_packing.py \
  --output /tmp/r9_streaming_packing_optimized.json
LEAN_BIN=/path/to/lean-4.35.0/bin/lean python scripts/validate_conditional_expectation_lean.py
elan run leanprover/lean4:v4.35.0 lean proofs/ConditionalExpectationSelection.lean
elan run leanprover/lean4:v4.35.0 lean proofs/ConditionalChildShrink.lean
elan run leanprover/lean4:v4.35.0 lean proofs/ConditionalExpectationAverage.lean
PYTHONPATH=src python scripts/validate_tapered_v4.py --write validation/r9_eight_wire_v3.json
PYTHONPATH=src python scripts/validate_tapered_v4.py --replay validation/r9_eight_wire_v3.json
```

Build and verify the complete release after all source and evidence edits:

```sh
python scripts/build_release.py
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

The co-delivered hashes are consistency checks, not signatures or proof of
origin. The archive SHA-256 is reported outside the archive because a ZIP
cannot contain its own final digest without a self-reference.

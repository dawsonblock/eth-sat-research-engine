# R9.1 refinement audit

## Scope and source identity

This is a partial R9.1 upgrade, not an implementation of the full theorem.
The available baseline archive was the packing-stage ZIP; its recorded digest
is `5ab628eb3bd82e07b3119926ec41b9c0024b23893d4a3381f4862c719b042e92`.
The expected R9.1 digest `0e4a06fc7f76a3e6d77be06a8cdf914aab3e32f5397bc9a91475eb766c24f1fd`
and a separately named CI-guard archive were not available. Baseline archive
checks are recorded in `validation/r9_1_baseline.json`.

The vendored source is `paper/quantitative-contraction.tex` with pinned
SHA-256 `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
Use its labels (`lem:tensor-packets`, `eq:tensor-packing-conditions`,
`app:tensor`) rather than historical Appendix-D numbering.

## Lean results and executable boundary

The proof gate compiles 22 modules under Lean 4.35.0, checks required theorem
and contract reports, and accepts only `propext`, `Classical.choice`, and
`Quot.sound`. Theorems and exact axiom reports are in
`validation/r9_conditional_expectation_proof.json`.

`D3PythonOrder.lean` preserves the historical graph order and adds a separate
sorted tagged order. It proves coverage, uniqueness, row-prefix/column-suffix
shape, edge-permutation invariance and the 22/16/16/12 three-edge fixture.
`D3PythonScoreModel.lean` proves the Lean-transcription identity
`pyCandidateScore_eq` to `concreteD3ScoreCandidate`, including the
`wordMatches_range_any` alignment lemma. `D3PacketBijection.lean` proves the
bounded padded-slot to packet-position bijection.

These are kernel-checked claims about the Lean definitions. The line-by-line
audit and finite Lean/CPython differential test do not prove that arbitrary
CPython bytecode executes the Lean model. Full-run selection and state
transition correspondence remain open, as does any C++-to-Lean refinement.
The correct qualification is `MODEL_REFINEMENT_PROVED` for the Lean model and
`EXECUTABLE_REFINEMENT_NOT_PROVED` for the Python/C++ implementations.
Further detail is in `docs/R91_REFINEMENT_AUDIT.md`.

## Native scorer

The C++20 backend provides an exact direct candidate scorer and a batched
one-vertex score evaluator. Both use `cpp_int`; Python remains available as an
explicit reference/fallback. The optional pybind11 interface bounds sequence
lengths before conversion; the ctypes interface uses the bounded Python
wrapper. The rational certificate checker imports neither production scorer.

V3 direct work units and V4 batch work units have distinct version identifiers.
The V4 checker independently recomputes the native work counter and separately
recomputes every score over rationals. Native limits include 100,000 edges,
10,000 vertices per side, 100,000 candidates, one million pair records,
64 MiB batch output, and 100 million conservative work units. No partial
result is returned when a cap or certificate check fails.

## Current R9.1 evidence

The reproducible local results are in:

* `validation/r9_1_proof_gate.json` — copied from the exact 22-module gate run;
* `validation/r91_python_model.json` — finite differential over the current
  12-case corpus;
* `validation/r9_1_differential.json` — pybind and ctypes candidate-score
  comparisons, complete fixture replays and large integer checks;
* `validation/r91_benchmarks.json` — repeated Python/direct/batch timings with
  separate work metrics;
* `validation/r91_release_evidence.json` — fail-closed aggregate gate record.

Every finite test is bounded evidence. These results do not prove the universal
packing lemma, the global edge-to-packet assignment, recursive contraction,
Hermite recovery through arbitrary depth, termination, or the theorem's
complexity bound.

## Remaining proof and implementation obligations

The first-minimizer selection lemma and full Python run simulation are still
open. The Lean packet bijection concerns the local padded-slot address space;
composition with the actual edge-to-class packet builder is still open.
Multilevel child contraction, source-scheduled tapered recovery, termination,
complete bit-time/space bounds and the outer #k-SAT reduction are not
implemented or qualified. Theorem mode remains disabled. See
`docs/R9_2_R9_4_PROOF_OBLIGATIONS.md`.

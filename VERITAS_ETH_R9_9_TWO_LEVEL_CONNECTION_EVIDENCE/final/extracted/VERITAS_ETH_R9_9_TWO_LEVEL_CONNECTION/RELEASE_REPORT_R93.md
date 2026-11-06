# VERITAS-ETH R9.3 — packet model correctness, partial theorem implementation

**Overall theorem qualification: BLOCKED. Theorem mode remains disabled.**
This is a complete source-tree release containing a tested implementation and
new universal combinatorial Lean proofs. It is not a completed implementation
of the OpenAI ETH theorem.

## Baseline and source

Input: `VERITAS_ETH_R9_2_PACKET_ADDRESS_PARTIAL_FULL_UPGRADED.zip`, SHA-256
`2886f4721f82f3229b0c32082d4cf3183c3c79c1054c8ee1191529859a03e9f0`.
CRC, path safety, duplicate-name and symlink checks passed. Both ordinary and
`python -O` manifest verification passed on a freshly extracted baseline:
652 file hashes. No original member was removed. The historical 1,216-test
baseline count was not independently rerun before modification in this turn.

The supplied R9.3 add-on ZIP was not present; the work was implemented against
the actual R9.2 source. The manuscript pin remains
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The mathematical address convention follows `lem:tensor-packets`.

## Changes

* Added a bounded immutable global edge-occurrence index and independent
  padded-domain audit, retaining repeated edges as distinct indexed entries.
* Added seven Lean modules: occurrence ranks, numeric bit inverses, numeric
  slot composition, complete packet model, computed padding, first-minimum
  selection, and separately stated mathematical contracts.
* Proved `r93_constructed_edge_contract`: every valid indexed entry in a
  common-width class sequence receives a valid, unique packet address and
  decodes back to that index. Its padding premises are derived from the
  computed maximum class load. Proved the occupied-slot reverse implication
  and the characterization of unoccupied padding.
* Compared actual Lean numeric addresses and heights against both Python
  builders. Added corruption, ordering, duplicate, capacity, and budget tests.
* Preserved both existing labelers and documented their different choices.
  The new first-minimum proof concerns the Lean whole-word list; it does not
  identify the separate coordinate-at-a-time Python algorithm with that list.
* Extended the pinned proof gate to 30 modules, retaining failure-cleared
  qualification flags and adding a `True`-substitution fault for the computed
  packet theorem. CI runs the packet differential as well as the proof gate.
* Corrected the README's old appendix-numbering and formula-test overclaims.

See [the exact mathematical and implementation audit](docs/R9_3_PACKET_CORRECTNESS.md)
and [remaining obligations](docs/R9_2_R9_4_PROOF_OBLIGATIONS.md).

## Reproduced local results

Host: macOS arm64. Primary Python: 3.12.0. Lean: 4.35.0,
commit `eb6cafb7290e8bd5f2937522d8d804f58f02bafc`. Exact compiler/CMake versions
are in `validation/r93_native_build.json`. All commands below exited zero.

| Check | Executed result | Time |
|---|---|---|
| Full Python 3.12 suite | 1,237 passed; zero skips/failures | 189.59 s |
| Full isolated Python 3.13.13 suite | 1,233 passed; four initially skipped | 93.36 s |
| All four skipped 3.13 cases, with Lean and matching pybind supplied | Four passed | 86.18 s |
| New packet tests under Python `-O` | 20 passed; standard pytest assertion warning | 0.24 s |
| Lean proof gate | 30 modules, 227 audited axiom reports | 55.77 s |
| Packet-model differential | 446 comparisons over 30 fixture runs; 2,528 independently audited padded-slot visits | 54.10 s |
| Native score differential | 1,296 cases; 12 rational certificate replays; pybind and ctypes | 0.053 s |
| Existing Lean/CPython score differential | 12 cases, zero mismatches | 34.31 s |
| Native C++ self-tests | Passed for the 3.12 and 3.13 builds | Build logs/local evidence |
| Existing finite v3.2 bond validation | 40 instances and tamper rejection passed | Not timed separately |
| Finite eight-wire execution and V3 replay | Exact residue `((1,0,0,0,0),)`; replay passed | 13.90 s / 14.96 s |

The Python 3.13 full-suite result and four-case follow-up are separate runs,
not a claim of one uninterrupted 1,237-case run. The system Homebrew 3.13
installation failed to load `pyexpat`; an isolated uv-managed interpreter was
used. Its four initial skips were two Lean compiler faults and two optional
pybind boundary checks. Both fault-injection cases genuinely compiled altered
proof trees and confirmed that the full proof gate rejected them.

The eight-wire run retained 3,074 tuples, generated 12,297 recursive calls,
reached depth one, and used a maximum precision of 521 bits. Its 2,299,570
observed work units remain an incomplete ledger. Point identity coverage is
`PARTIAL_OR_NOT_CHECKED`; V3 replay is a shared-code replay with
`HASH_MATCH_UNSIGNED` trust, not independent proof. Measured peak RSS was
121,372,672 bytes for execution and 230,031,360 bytes for replay; no hard memory
limit was enforced. This is regression evidence, not multilevel recursion
qualification.

The existing scorer benchmark was rerun on five fixtures with three repeats;
all exact results and direct work counters agreed. Detailed measurements,
including small-input overhead, are in `validation/r91_benchmarks.json`. No
new speedup or asymptotic claim is made by this release.

## Release gates and remaining risk

| Gate | Evidence | Result | Remaining risk |
|---|---|---|---|
| Baseline integrity | Fresh extraction and both manifest checks | PASS | Hashes do not authenticate provenance. |
| Canonical executable labeling | Sorted-order Lean model, first-minimum theorem, finite trace tests | BLOCKED | General candidate enumeration and full Python-run correspondence remain unproved; two builders have different semantics. |
| Complete edge assignment | `r93_constructed_edge_contract` | PASS — Lean model | Executable source-to-model bridge remains open. |
| Injective addresses | `encodeEdge_injective`, repeated-occurrence differential tests | PASS — Lean model | Not a theorem about arbitrary CPython or C++ machine code. |
| Surjective occupied-slot mapping | `r93_occupied_packet_contract`, padding inverse laws | PASS — Lean model | Explicit finite-domain cardinality theorem is not supplied. |
| Executable refinement | 446 Lean/Python comparisons and independent finite audits | BLOCKED | Tests do not prove universal executable agreement. |
| Full recursive counting theorem | Existing fail-closed theorem branch | BLOCKED | Source-complete modes, all-node contraction/recovery, precision, termination, outer reduction, and complexity proofs remain. |
| Local regression | Recorded full suites, native tests, and mathematical scripts | PASS | No hosted CI run or branch-protection enforcement was performed here. |

The model PASS rows are not five completed source-to-executable acceptance
gates. `universal_packing_lemma_proven`, `universal_python_refinement_proven`,
recursive correctness, complexity qualification, and theorem-mode flags remain
false. No failed proof obligation has been replaced with direct enumeration.

## Artifacts and reproduction

* `validation/r93_release_evidence.json`: result inventory, scope, artifact
  hashes, test-source hashes, source digest and explicit blockers.
* `validation/r9_conditional_expectation_proof.json`: exact module hashes,
  compiler/version checks and axiom reports.
* `validation/r9_3_packet_differential.json`: fixed policy, source manifest,
  30 fixture records, commands and 446 comparisons.
* `validation/r93_pytest_*.xml` / `.log`: executed outcomes and skipped-case
  follow-up. Packaged logs normalize local paths and remove hostnames.
* `validation/r93_eight_wire_v3.json`: self-contained finite transcript.

Run the commands in [the audit](docs/R9_3_PACKET_CORRECTNESS.md#reproduction).
For Python 3.13, use a working isolated interpreter and a matching pybind build,
and set `LEAN_BIN` to the repository-pinned executable if it is absent from
that environment's PATH. Use `VERITAS_D3_CPP_BUILD_DIR` for a separate native
build. The checked source files do not depend on machine-specific paths.

The complete source ZIP is named
`VERITAS_ETH_R9_3_PACKET_MODEL_PARTIAL_FULL_UPGRADED.zip`.
`scripts/build_release.py` writes deterministic member metadata, internal
manifests, and a sidecar with the archive hash and every member hash. Final
CRC, safety, clean-extraction and manifest results are recorded next to the
ZIP in its external `.verification.json`, avoiding an archive self-hash.
Caches, virtual environments and native/compiler binaries are excluded.

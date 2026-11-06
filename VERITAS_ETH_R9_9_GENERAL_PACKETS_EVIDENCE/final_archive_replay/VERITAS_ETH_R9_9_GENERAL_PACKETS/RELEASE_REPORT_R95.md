# VERITAS-ETH R9.5 — source recipe and leaf execution (partial)

**Implemented and tested bounded entry/leaf execution. The full theorem implementation remains BLOCKED.** This report supersedes earlier release metrics for this build; older reports and evidence are preserved as historical records.

## Changes

The R9.4 `SourceNode` interface admitted opaque recipe bytes but could not evaluate them. R9.5 adds a canonical immutable recipe format, exact packet coefficient extraction at creation precision, an explicit adapter from existing descriptions, and a leaf executor gated by the source leaf threshold. It separately checks the original root coefficient domain. Every failure has no accepted value; active source calls and theorem requests remain inconclusive.

An independent oracle uses integer polynomial reduction, full formal mode-polynomial convolution and variable elimination. New Lean model lemmas prove coordinate-lift preservation/roundtrip and demonstrate nonadditivity/nonmultiplicativity; independently typed contracts reject replacement with `True`. The new fault is included in the full proof-gate fault suite. These are model results, not executable refinement.

Original paper files, existing mathematical Python modules, C++ scorer and theorem-mode guard were preserved. Baseline packaging was checked against SHA-256 `727abadd550efd7870add0bef4d4a16e30c272ecd77b1d165089337c27c81549`: 738 ZIP members, valid CRCs, no traversal/duplicates/symlinks, 736 JSON-manifest entries matched. No original file was deleted. The text manifest additionally covers the JSON manifest. A fresh pre-change full test suite was not run this turn; R9.4 results remain historical evidence.

## Executed validation

Machine: Apple M2 Pro, 16 GiB RAM, macOS 26.2 arm64. Python 3.12.0 / 3.13.13, Lean 4.35.0 (`eb6cafb7290e8bd5f2937522d8d804f58f02bafc`), AppleClang 21.0.0; complete versions in `validation/r95_environment.json`.

| Check | Actual result | Scope / limit |
|---|---|---|
| Full Python 3.12, native binding + pinned Lean present | **1,375 passed, no skips**, exit 0; 375.91 s command wall time; 1,394,081,792 bytes peak RSS reported by time | Includes all five compiled theorem-substitution faults |
| Initial full Python 3.13 | **1,368 passed, 7 skipped**, exit 0; 99.73 s; 233,029,632 bytes | Five Lean tests lacked the shell PATH; two optional binding tests lacked a build. Not reported as a fully unskipped run |
| Python 3.13 native and new-component follow-up | **129 passed**, exit 0 | Covers optional binding checks and all 99 new recipe/leaf/grid cases; compiled Lean faults ran in Python 3.12 |
| Optimized Python fault/API checks | **118 passed**, exit 0 | New tests and proof-audit tests under `python -O`; pytest warning preserved |
| Lean proof gate | **36 modules PASS**, 176.33 s | Exact contracts and permitted transitive axioms checked; formal-model scope only |
| R9.4 run/domain comparisons | **887 comparisons PASS** | 23 finite runs, seven complete bounded domains |
| R9.3 packet comparisons | **446 comparisons PASS** | Finite Lean/Python packet vectors |
| C++20 builds/self-tests | **PASS** with separate Python 3.12 and 3.13 pybind modules | macOS builds only; Linux/Windows hosted builds not reproduced |
| C++ differential + rational replay | **1,296 scores, 12 certificate replays PASS** | Both pybind and C ABI checked, exact integers |
| New independent recipe/leaf/grid validation | **160 entry equalities, nine CNF leaf counts, 258 Hermite points PASS** | Finite checks with explicit mathematical premises |
| Selected 4/6/8-wire point oracles | **3/3 selected points PASS**, write + replay | One node/point per size; not all-node coverage |
| Eight-wire V3 experiment | **PASS**, expected residue `((1,0,0,0,0),)`; replay PASS | Depth one; this transcript separately reports 0/50 direct point checks |
| Dense reconstruction 8/10/12 wires | **PASS**, counters 579,584 / 4,033,536 / 24,813,568 | Scalar counters; direct half-edge checks at 10/12 remain blocked by the pair cap |
| Legacy v3.2 / v2.8 scripts and aggregate gate | **PASS** | Inherited finite checks; aggregate includes fresh proof-source hashes |

The eight-wire experiment retains 12,297 calls, 3,074 tuples, 50 independent tuple-count checks, maximum precision 521, maximum child size 6 and 2,299,570 incomplete-accounting work units. The separate pinned point at `t=-1`, `p=521`, `zeta=(1,0,0,0,0)` has six modes, 64 tuples and both values `((169600000000,0,0,0,0),)`. A selected-point oracle does not upgrade the eight-wire transcript to complete point coverage.

C++ benchmarks were regenerated with exact equality required. This release makes no new speedup claim: concurrent validation, finite workloads and incomplete bit-work accounting limit performance interpretation. All RSS figures are measurements, not enforced memory limits.

## Release gates and remaining risks

| Gate | Evidence | State | Remaining risk |
|---|---|---|---|
| Source identity | All four LaTeX blobs match the pinned current upstream commit | PASS | Hash agreement is not a proof of the paper or trusted executor |
| Entry semantics and source leaves | Independent polynomial/elimination oracle, mutations, CNF counts | PASS (bounded) | No universal source-to-executable refinement or entry-cost theorem |
| Formal contracts | 36-module gate, five `True` substitution faults | PASS (models) | New packet algorithm itself is not kernel-verified |
| Existing finite integration | V3 write/replay, selected points, packing/CPP checks | PASS (finite) | No source-active multilevel recursion |
| Complete theorem execution | Listed in `docs/R95_REMAINING_OBLIGATIONS.md` | **BLOCKED** | Universal mode/child/recovery proofs, executable bridge, outer reduction and bit/space bounds |
| Hosted CI / required branch checks | Workflow updated; local commands reproduced | NOT REPRODUCED | No hosted workflow or branch-protection claim |
| Release integrity | Canonical manifests + fresh extraction verification | See archive verification sidecar | Hashes are not signatures |

## Reproduce

After installing the repository-pinned Lean toolchain and Python test dependencies:

```sh
python -m pip install -e '.[test]' pybind11
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
lean --version
PYTHONPATH=src LEAN_BIN="$(command -v lean)" python -m pytest -q -o addopts='' -rs
python scripts/validate_conditional_expectation_lean.py --output validation/r9_5_proof_gate.json
python scripts/validate_r95_recipes.py
python scripts/validate_r94_foundation.py
PYTHONPATH=src python scripts/validate_r82.py --write validation/r95_selected_points.json
PYTHONPATH=src python scripts/validate_tapered_v4.py --write validation/r95_eight_wire_v3.json
PYTHONPATH=src python scripts/validate_tapered_v4.py --replay validation/r95_eight_wire_v3.json
PYTHONPATH=src python scripts/validate_dense_v382.py --wires 8 10 12
python scripts/build_release.py --output-name VERITAS_ETH_R9_5_RECIPE_EXECUTION_PARTIAL_FULL_UPGRADED.zip
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

Regenerating measured evidence changes its timing bytes and therefore the release hash. The builder is deterministic for a fixed source/evidence tree. Generated manifests do not certify the origin of the compiler or the truth of stored reports.

Read `docs/R95_SOURCE_MATH_AUDIT.md` for the equations, source scope and trust boundary; `docs/R95_RECIPE_API.md` for the executable API; and `validation/r95_qualification.json` for machine-readable command outcomes and evidence hashes. No universal subexponential counting or polynomial-space qualification is asserted.

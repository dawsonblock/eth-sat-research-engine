# R9.6 test matrix

Every row records the exact command, the environment, and the observed result.
A skip is listed as a skip with its reason; it is never counted as a pass.

Environment for all rows unless stated otherwise:

| Item | Value |
|---|---|
| OS | macOS 26.2, arm64 (Darwin 25.2.0) |
| Python | CPython 3.12.0 (pyenv) |
| pytest | 9.2.0 |
| Dependencies | fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.3, httpx 0.28.1, networkx 3.7, hypothesis 6.170.14, setuptools, wheel, build |
| C++ | Apple clang 21.0.0, CMake 4.2.1, Boost (Homebrew), pybind11 3.1.0 |
| Lean | 4.35.0, commit `eb6cafb7290e8bd5f2937522d8d804f58f02bafc` (elan 4.2.4) |
| Native build | `/Users/dawsonblock/VERITAS_R96_WORK/build/cpp` (outside the release tree) |
| Evidence root | `/Users/dawsonblock/VERITAS_R96_WORK/evidence` (outside the release tree) |

`PYTHONPATH=src` is used everywhere so the checkout is the import root and no
editable install is required.

---

## 1. Baseline (pristine R9.5 extraction)

| Check | Command | Result |
|---|---|---|
| Archive SHA-256 | `shasum -a 256 …R9_5…zip` | `5d5b88c7…4ece3756` — matches the published sidecar |
| Safe extraction | `python tools/safe_extract.py … --expected-sha256 …` | 821 members, 102,050,410 bytes, CRC ok, no traversal/symlink/duplicate/bomb, 0.5 s |
| Release manifest | `python scripts/verify_manifest.py` | `PASS: 820 complete file hashes match release manifest` |
| Full suite | `python -m pytest -o addopts='' -q` | **1343 passed, 32 skipped, 0 failed** in 104.7 s |
| Lean / pybind11 | — | **NOT_RUN** at baseline time (no toolchain installed); recorded as a blocker, not a pass |

## 2. Red reproductions (each on a disposable copy, before the repair)

| # | Defect | Command | Observed |
|---|---|---|---|
| R1 | CI mutates a release input before verifying the manifest | `verify_manifest.py` → `validate_v08.py` → `verify_manifest.py` | `PASS` → (validator rewrites `validation/validation_v08.json`) → `FAIL: checksum mismatch` |
| R2 | Wheel lacks the pinned manuscript | isolated venv + wheel, `contract_source_leaf` on the empty-edge node | `{"status": "INCONCLUSIVE_SOURCE_MISMATCH", "reason": "pinned manuscript is absent or changed"}` |
| R3 | Source scalars escape the coefficient budget | `compile_entry` with `EntryLimits(max_coefficients=1)` and four source scalars | **admitted**, returned `((2, 0),)` |
| R4 | Exponential row enumeration | `[z](1-z)^15`, degree 2, jet length 2, default limits | `INCONCLUSIVE_RESOURCE_LIMIT: entry work/time budget exhausted` after 2.16 s |
| R5 | Point coverage in the eight-wire transcript | read `validation/r95_eight_wire_v3.json` | `points_checked: 0, points_skipped: 50, points_total: 50`, `PARTIAL_COVERAGE` |
| R6 | Source-active schedule unreachable | `active_parameter_contradiction()` | `max_lambda = 16` (default) / `1024` (ceiling) vs `required = 131072` |

## 3. Green regression suites (R9.6)

| Suite | Command | Result |
|---|---|---|
| Release integrity | `pytest -q tests/test_r96_release_integrity.py` | **14 passed** |
| Manuscript resource | `pytest -q tests/test_r96_manuscript_resource.py` | **17 passed** |
| Coefficient budget | `pytest -q tests/test_r96_coefficient_budget.py` | **31 passed** |
| Packet coefficients | `pytest -q tests/test_r96_packet_coefficients.py` | **73 passed** |
| Serialization / validators (Hypothesis) | `pytest -q tests/test_r96_serialization.py` | **28 passed** |
| Parent-to-all-children | `pytest -q tests/test_r96_parent_child.py` | **23 passed** |
| Source regime | `pytest -q tests/test_r96_source_regime.py` | **10 passed** |
| Hermite audit | `pytest -q tests/test_r96_hermite_audit.py` | **21 passed** |
| R9.5 inherited (recipes/leaf/grid/state) | `pytest -q tests/test_r95_*.py tests/test_r94_source_state.py` | **122 passed** |

## 4. Full suite, three configurations

| Configuration | Command | Result |
|---|---|---|
| No Lean, no C++ build | `pytest -o addopts='' -q` | **1560 passed, 32 skipped, 0 failed** (106.6 s) |
| Lean on `PATH` | same, `PATH="$HOME/.elan/bin:$PATH"` | **1565 passed, 27 skipped, 0 failed** (366.2 s) |
| Lean + C++ build dir | same, `PATH=… VERITAS_D3_CPP_BUILD_DIR=…/build/cpp` | **1590 passed, 2 skipped, 0 failed** |

Skip reasons, all environmental, none hidden:

* 25 × `tests/test_r91_cpp_backend.py`: *C++ scorer is not built* — the variable
  `VERITAS_D3_CPP_BUILD_DIR` was not set in that run.  With it set, 28 of those
  cases pass and 2 remain skipped.
* 2 × `tests/test_r91_cpp_backend.py`: *optional pybind11 module is not built* —
  the pybind module was compiled against a different interpreter ABI; the
  ctypes C ABI was exercised instead.

Delta versus baseline: **+222 test cases**, same skip count when the native
backend is absent, **0 regressions**.

## 5. Lean proof gate

| Check | Command | Result |
|---|---|---|
| Toolchain | `lean --version` | `Lean (version 4.35.0, arm64-apple-darwin24.6.0, commit eb6cafb…, Release)` — exactly the `lean-toolchain` pin |
| 36-module compile + axiom audit | `python scripts/validate_conditional_expectation_lean.py` | **PASS**, 58.8 s, axioms `propext`, `Classical.choice`, `Quot.sound` only |
| Refinement flag | same evidence | `lean_python_builder_refinement_proven: false` (correct — no refinement proved) |
| Binary authentication | same evidence | `lean_binary_authenticated: false`, `lean_binary_path_recorded: false` (honest: the downloaded toolchain is not publisher-verified) |

## 6. Native C++ backend

| Check | Command | Result |
|---|---|---|
| Configure | `cmake -S cpp -B …/build/cpp -DCMAKE_BUILD_TYPE=Release -Dpybind11_DIR=…` | ok |
| Build | `cmake --build …/build/cpp --parallel 4` | ok, `-Werror` clean |
| Self-test | `…/build/cpp/veritas_d3_selftest` | `PASS` |
| Differential | `VERITAS_D3_CPP_BUILD_DIR=… python scripts/validate_r91_cpp.py --output …` | `PASS_FINITE_CPP_DIFFERENTIAL`, backend `cpp-ctypes`, 6 certificate replays, large-integer exact on both sides |
| Backend regressions | `VERITAS_D3_CPP_BUILD_DIR=… pytest -q tests/test_r91_cpp_backend.py` | 28 passed, 2 skipped |

## 7. Release-integrity sequence (R9.6, on the built release)

| Step | Command | Result |
|---|---|---|
| Pre-verify | `python scripts/release_integrity.py verify` | `PASS: 845 release inputs, 0 mismatched, 0 missing, 0 unlisted, 0 absent` |
| Optimized pre-verify | `python -O scripts/release_integrity.py verify` | identical output |
| Snapshot | `python scripts/release_integrity.py snapshot --output …` | 846 entries (845 + the manifest itself) |
| Validators | `VERITAS_EVIDENCE_DIR=… python scripts/validate_v08.py` etc. | all pass; every artifact lands outside the tree |
| Manifest | `python scripts/verify_manifest.py` | `PASS: 845 complete file hashes match release manifest` |
| Post-compare | `python scripts/release_integrity.py compare --snapshot …` | `PASS: release inputs unchanged during the job` |

## 8. R9.6 aggregate gate

| Check | Command | Result |
|---|---|---|
| Hardening gate | `python scripts/validate_r96_hardening.py` | 7 of 8 required checks `PASS`; `lean_toolchain` `PASS`; see `evidence/r96_hardening.json` |
| Independent adversarial checker | `python adversarial/check_r96_independently.py --evidence …` | `RESULT: PASS (all independent checks agree)` |
| Benchmarks | `python scripts/benchmark_r96.py` | packet results agree; 26 #SAT cases, 13 brute-force verified, 0 incorrect; 1 explicit refusal probe returns no value |

## 9. Direct point coverage

| Artefact | Points checked / required | Classification |
|---|---|---|
| R9.5 eight-wire transcript (unchanged, historical) | 0 / 50 | `PARTIAL_COVERAGE` |
| R9.6 certified two-wire fixture | **8 / 8** | `FULL_COVERAGE` |
| R9.6 certificate consumer, after any mutation | 0 / 0 or partial | `PARTIAL_COVERAGE`, `valid: false` |

The R9.6 number is for **one recursion level on one bounded fixture**.  It does
not repair the historical eight-wire transcript and it does not generalise.

## 10. Cross-platform

| Platform | Status |
|---|---|
| macOS 26.2 / arm64 | **RUN** — all results above |
| Linux x86-64 | **NOT_RUN** in this session (no host available) |
| Windows | **NOT_RUN** in this session |

The prior R9.5 Linux result (1368 passed / 7 skipped / 0 failed after the C-ABI
build) is *inherited evidence only* and was not reproduced here.

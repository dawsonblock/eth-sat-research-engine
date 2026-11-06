# VERITAS-ETH R9.1 partial release report

## Release scope

This is a tested R9.1 research upgrade, not an implementation of the full
OpenAI theorem. The theorem path remains disabled and fail-closed. This
release adds a kernel-checked Lean score model, a C++20 finite scoring
backend, differential checks, and local packet-address proofs. It does not
prove that Python or C++ executables refine Lean, and it does not implement
the full packet map, recursive contraction, Hermite recursion, or asymptotic
complexity argument.

The expected input archive SHA-256
`0e4a06fc7f76a3e6d77be06a8cdf914aab3e32f5397bc9a91475eb766c24f1fd` did not
match an archive in the workspace. The available packing-stage archive had
SHA-256 `5ab628eb3bd82e07b3119926ec41b9c0024b23893d4a3381f4862c719b042e92`.
No separately named CI-guard ZIP was present. Its CRCs, safe paths, duplicate
names, symlinks and 596 manifest hashes were checked; see
`validation/r9_1_baseline.json`.

The pinned manuscript source is `paper/quantitative-contraction.tex`,
SHA-256 `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The source tree was not changed.

## Validation reproduced for this package

Environment: macOS 26.2 arm64, Python 3.12.0, Lean 4.35.0,
AppleClang 21.0.0, CMake 4.2.1, C++20, Boost 1.90.0 and pybind11 3.1.0.

| Gate | Result | Evidence and limit |
|---|---|---|
| Python full suite | **PASS**, 1,186 passed, 1 skipped in 106.27 s; exit 0 | Peak RSS 289,144,832 bytes, measured by `/usr/bin/time -l`; the skipped case is the separately run Lean fault-injection test. |
| Lean fault injection | **PASS**, 1 test in 37.82 s | Replaced the arbitrary-order port theorem with `True`; the full gate rejected it and cleared the dependent proof flags. |
| Pinned Lean proof gate | **PASS**, 22 modules in 28.92 s | `validation/r9_1_proof_gate.json`; exact toolchain and manuscript pin match; no `sorryAx`; reported axioms are `propext`, `Classical.choice`, and `Quot.sound`. |
| Lean-model/CPython differential | **PASS**, 12 cases, 0 mismatches | `validation/r91_python_model.json`; finite corpus only. |
| C++20 build and CTest | **PASS**, C ABI and pybind11 built; self-test and CTest 1/1 pass | AppleClang/macOS only; Linux and Windows builds were not run here. |
| C++ focused integration tests | **PASS**, 49 tests in 4.66 s | `validation/r9_1_cpp_focused_tests.log`; pybind11 backend loaded. |
| Python/C++/rational differential | **PASS**, 1,296 score cases, 12 fixture executions and 12 independent rational replays | Both pybind and ctypes paths; large integer exactness passed; see `validation/r9_1_differential.json`. |
| Benchmark | **PASS**, five inputs, three repeats, exact outputs | See `validation/r9_1_benchmarks.json`; local finite timings, not a general speed guarantee. |
| Release evidence aggregator | **PASS** | `validation/r91_release_evidence.json`; proof-model flags may be true, executable-refinement flags remain false. |
| GitHub-hosted CI | **NOT RUN** | The workflow has a separate pinned Lean job and always-uploaded proof evidence. An active release-branch ruleset requires `lean-proof`; its readback is in `validation/r9_1_release_branch_ruleset.json`. |

The five benchmark medians (milliseconds) were:

| Fixture | Python reference | C++ direct | C++ batch |
|---|---:|---:|---:|
| tiny-r2-a1 | 0.095 | 0.114 | 0.087 |
| small-r2-a1 | 4.705 | 0.797 | 0.566 |
| small-r3-a1 | 5.724 | 1.047 | 0.577 |
| medium-r2-a2 | 47.287 | 3.425 | 1.502 |
| medium-r3-a2 | 53.073 | 4.865 | 1.330 |

The batch and direct paths use distinct versioned work metrics. Candidate
scores were exact and the direct work counters matched their reference
metrics. These counts do not account for complete bit work, and incident
edge-pair processing can remain quadratic in the edge count. The tiny input
was slower through the C++ direct call; no general speedup claim follows.
The local CMake configure emitted the nonfatal `CMP0167` development-policy
warning; all requested targets built and the self-test/CTest passed.

## Implemented proof and software scope

`D3PythonOrder.lean` preserves the old vertex-list semantics and proves a
separate canonical sorted tagged order, its endpoint coverage and uniqueness,
edge-permutation invariance, a sorted-order port bound, and the compiled
three-edge trace fixture.

`D3PythonScoreModel.lean` proves `wordMatches_range_any` and
`pyCandidateScore_eq` for the Lean transcription and its abstract Lean score.
This is **MODEL_REFINEMENT_PROVED**. The line-by-line source audit and finite
12-case differential are useful evidence, but do not prove that arbitrary
CPython bytecode executes those Lean definitions. Full-run first-minimizer
selection and state-transition correspondence remain open.

The C++ scorer uses exact multiprecision integers, bounded inputs, explicit
backend selection and a Python fallback. It is **CPP_TESTED**, not
formally verified. The independent rational certificate checker does not
call either production scorer.

`D3PacketBijection.lean` proves the local bijection between padded class-slot
offsets and packet/slot addresses. The explicit edge-to-class map and its
composition with the concrete packet builder are not proved, so the global
`PACKET_BIJECTION` qualifier remains false.

## Qualification table

| Qualifier | Status |
|---|---|
| CI workflow configuration | `TESTED_BY_STATIC_AUDIT`; hosted CI `NOT_RUN` |
| Python | `PYTHON_TESTED` |
| C++ | `CPP_TESTED` on macOS arm64 |
| Lean model | `LEAN_KERNEL_CHECKED`, 22 modules |
| Lean model score correspondence | `MODEL_REFINEMENT_PROVED` |
| Python-to-Lean executable refinement | `EXECUTABLE_REFINEMENT_NOT_PROVED` |
| C++-to-Lean executable refinement | `EXECUTABLE_REFINEMENT_NOT_PROVED` |
| Full run/selection correspondence | `NOT_PROVED` |
| Global packet bijection | `NOT_PROVED` |
| Recursive contraction, recovery and termination | `NOT_IMPLEMENTED` |
| Complete bit-time and peak-space proof | `COMPLEXITY_NOT_ESTABLISHED` |
| Theorem mode | `DISABLED` |

The next R9.1 dependency is a proved first-minimizer and state-transition
simulation plus a justified Python-to-model bridge. R9.2 requires the global
edge-to-packet bijection; R9.3 and R9.4 remain blocked on recursive
contraction/recovery and complete cost proofs. See
`docs/R9_2_R9_4_PROOF_OBLIGATIONS.md`.

## Reproduction

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release \
  -DVERITAS_D3_BUILD_PYBIND=ON \
  -Dpybind11_DIR="$(python -c 'import pybind11; print(pybind11.get_cmake_dir())')"
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
ctest --test-dir build/cpp --output-on-failure
LEAN_BIN=/path/to/lean-4.35.0/bin/lean \
  python scripts/validate_conditional_expectation_lean.py \
  --output validation/r9_1_proof_gate.json
LEAN_BIN=/path/to/lean-4.35.0/bin/lean \
  python scripts/validate_r91_python_model.py \
  --output validation/r91_python_model.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/validate_r91_cpp.py \
  --output validation/r9_1_differential.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/benchmark_r91_scorer.py \
  --output validation/r9_1_benchmarks.json --repeats 3
PYTHONPATH=src python -m pytest -q -o addopts='' -ra
LEAN_BIN=/path/to/lean-4.35.0/bin/lean PYTHONPATH=src \
  python -m pytest -q -o addopts='' \
  tests/test_lean_proof_gate_fault_injection.py
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/validate_r91.py
python scripts/build_release.py
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

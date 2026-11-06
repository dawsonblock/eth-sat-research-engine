# VERITAS-ETH R9.4 — source-foundation partial release

Implemented and tested: immutable source-state admission, general Lean-model
candidate order/tie correctness, complete keyed labeling-run correspondence,
and the complete radix-bounded padded packet-domain bijection/cardinality.
The existing finite solver, C++ scorer and theorem-mode refusal are preserved.
This is a complete repository archive of a **partial theorem implementation**.

## Qualification

| Gate | Executed evidence | Result | Remaining risk |
|---|---|---|---|
| Baseline identity | Input SHA-256, ZIP CRC/path/duplicate/symlink audit; 682 manifest entries; 30 Lean modules | PASS | Historical pre-change Python count was not independently rerun before edits |
| Source-state foundation | 23 new state tests; exact integer schedule, incidence, creation metadata and source pin checks | PASS, bounded admission | Recipe semantics, ancestry and entry-cost proof absent; no active executor |
| Candidate and keyed run models | General order, tie, update, run and trace proofs; independent typed contracts | LEAN-KERNEL-CHECKED | CPython/itertools/dict and machine-code correspondence is not proved |
| Complete finite packet domain | Separate domain enumerations, inverses, no duplicates, permutation and r^(2a)*H cardinality | LEAN-KERNEL-CHECKED | Python/C++ packet source refinement and implicit construction cost remain open |
| New finite differential | 887 comparisons; 23 runs with rational replay; 7 complete packet domains | PASS | Finite executable evidence |
| Existing packet comparison | 446 fresh Lean/Python codec comparisons | PASS | Finite executable evidence |
| Python 3.12.0 suite | 1,273 passed, 2 skipped, 0 failed/errors; 276.578 s | PASS with explicit skips | Optional binding absent from that run; separately checked below |
| Python 3.13.13 suite | 1,273 passed, 2 skipped, 0 failed/errors; 258.639 s | PASS with explicit skips | Same optional binding skips; separately checked below |
| C++20 and bindings | Fresh builds/self-tests; 30 focused tests on each Python; 1,296 scoring cases and 12 rational replays across ctypes/pybind11 | CPP_TESTED | macOS ARM64 only; no executable formal verification |
| Optimized Python | 61 focused cases and 2 kernel fault injections passed under python -O | PASS | Runtime/interpreter still trusted |
| Lean gate | All 34 modules passed; exact Lean 4.35.0 and manuscript pin; approved axioms only | PASS | Hash match does not authenticate compiler/executor |
| Existing eight-wire run | Residue ((1,0,0,0,0),), 12,297 calls, depth 1, 3,074 tuples; V3 replay passed | PASS, finite | Partial point coverage; not multilevel theorem evidence |
| Legacy validations | Smoke, v12/v13/v14/v15/v17/v19/v20/v23/v26/v28/v29/v32/v33 and 10,000-case script all exited 0 | PASS | Their historical qualification limits remain |
| CI workflow | New differential step added to the pinned Lean job with evidence upload | CONFIGURED / NOT RUN | Hosted Actions and server branch-protection enforcement not reproduced |
| Executable refinement | General Lean-model proof plus finite executable comparisons | BLOCKED | No verified extraction or source-to-model compiler bridge |
| Recursive theorem | Existing finite reconstruction only | BLOCKED | Universal modes, child identity, source Hermite composition and termination |
| Complexity / outer reduction | Partial counters and finite #SAT paths | BLOCKED | Complete bit-time, peak-space and arbitrary-density reduction proofs |
| Theorem mode | Guard unchanged byte-for-byte | DISABLED | INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED |

The new Python tests add 36 cases; two additional weakened-theorem fault
injections bring the inventory from the historical 1,237 to 1,275. The full
runs executed 1,273 cases each. The two skipped pybind11 cases were later
executed successfully in the separate 30-test runs on each interpreter;
we do not relabel the original full runs as zero-skip runs.

No new performance improvement is claimed. The five-instance scorer
benchmark was rerun with exact score/work equality, but the machine was
not isolated from other validation work. Its times and RSS are measurements,
not asymptotic bounds. The eight-wire write took 13.787 s with measured peak
RSS 117,604,352 bytes; replay took 15.095 s with 209,371,136 bytes. Its
2,299,570 observed work units remain incomplete accounting. No hard OS
memory limit was enforced.

Initial uninstalled-checkout commands lacking PYTHONPATH failed at import.
They were rerun with PYTHONPATH=src; initial smoke and eight-wire failure
logs are retained. New logs redact local path prefixes and host names only.
Warnings include the Python -O assertion warning, a Python 3.13 dependency
deprecation, and CMake/Boost policy warnings; none was treated as a pass
without a successful command exit.

## Artifacts and audit boundary

* `docs/R94_SOURCE_FOUNDATION_AUDIT.md`: exact mathematical contracts and trust boundary.
* `docs/R94_REMAINING_OBLIGATIONS.md`: next dependencies and blockers.
* `validation/r94_execution_summary.json`: executed counts, commands and qualifications.
* `validation/r9_4_proof_gate.json`: fresh 34-module proof evidence.
* `validation/r9_4_differential.json`: source-bound full-run/domain comparisons.
* `validation/r94_packet_differential.json`: fresh existing codec comparisons.
* `validation/r94_baseline_diff.json`: source preservation and changed-file inventory.
* `validation/r94_eight_wire_v3.json`: fresh finite transcript with its own V3 policy.

The original sealed R9.3 checkout and ZIP remain unchanged. Historical
reports retained inside this repository describe their own releases and
must not be used as fresh R9.4 evidence. `validation/r9_conditional_expectation_proof.json`
is a compatibility copy of the freshly generated R9.4 gate evidence;
`validation/r94_release_aggregate.json` checks its current source hashes.
The aggregate's legacy status name is retained for API compatibility.

The final ZIP is `VERITAS_ETH_R9_4_SOURCE_FOUNDATION_PARTIAL_FULL_UPGRADED.zip`.
Its adjacent `.manifest.json` records every archive member hash and the
archive SHA-256. The adjacent `.verification.json` records safe extraction,
standard/optimized manifest verification and fresh-extraction tests. These
external records avoid self-referential archive hashing.

## Reproduction from the extracted repository

Install the pinned Lean toolchain in `lean-toolchain` through elan, and
provide CMake, a C++20 compiler and Boost development headers. Use a fresh
Python environment for each version to reproduce both bindings.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]' pybind11
export PYTHONPATH=src
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
  -DPython_EXECUTABLE="$(command -v python)"
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
ctest --test-dir build/cpp --output-on-failure
lean --version
python scripts/validate_conditional_expectation_lean.py --output validation/r9_conditional_expectation_proof.json
python -m pytest -q -o addopts='' --junitxml=validation/reproduced_pytest.xml
python scripts/validate_r94_foundation.py --output validation/reproduced_r94_differential.json
python scripts/validate_r93_packet_model.py --output validation/reproduced_packet_differential.json
python scripts/validate_r91_cpp.py --output validation/r9_1_differential.json
python scripts/validate_r91_python_model.py
python scripts/benchmark_r91_scorer.py
python scripts/validate_r91.py --output validation/reproduced_aggregate.json
python -O -m pytest -q -o addopts='' tests/test_r94_source_state.py tests/test_r94_foundation_validation.py tests/test_lean_proof_gate_audit.py tests/test_r91_fresh_lean_evidence.py
python -O -m pytest -q -o addopts='' tests/test_lean_proof_gate_fault_injection.py -k 'D3KeyedRun or D3FinitePacketDomain'
python scripts/validate_tapered_v4.py --write validation/reproduced_eight_wire.json
python scripts/validate_tapered_v4.py --replay validation/reproduced_eight_wire.json
python scripts/validate_v32.py
python scripts/validate_10000.py
python scripts/smoke.py
```

Verify the shipped manifest **before** overwriting its evidence files. A
rerun produces new elapsed times and therefore changes those files. To seal
a new release after rerunning validation:

```sh
python scripts/build_release.py --output-name VERITAS_ETH_R9_4_SOURCE_FOUNDATION_PARTIAL_FULL_UPGRADED.zip
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

All tests above must report their actual outcomes. Passing them does not
change executable-refinement, recursive-theorem or complexity blockers.

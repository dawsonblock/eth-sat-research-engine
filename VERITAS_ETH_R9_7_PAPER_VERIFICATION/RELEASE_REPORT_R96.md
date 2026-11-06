# VERITAS-ETH R9.6 finite reductions and evidence repairs

This release repairs the five R9.5 audit findings and adds two executable finite reductions. The full source-active counting algorithm remains unimplemented. Source checkout execution, a clean installed wheel for source leaves, and a Linux Docker leaf were exercised locally.

## Baseline and fixes

The input was the 821-member R9.5 archive with SHA-256 `5d5b88c748414bb468dc063de59fe94974beede4934c2500346fc0da4ece3756`. All 819 JSON payload hashes and all 820 text-manifest hashes matched. Its selected-point command accepted the deliberately corrupted record, and its Lean aggregator accepted all three corrupted compiler reports in a fresh extraction. See [baseline reproduction](validation/r96_baseline_reproduction.json).

| Finding | R9.6 behavior | Evidence |
|---|---|---|
| Tampered saved point record | V2 checks the submitted schema, canonical artifact digest, semantic digest, source binding, policy, coverage and fresh arithmetic. Legacy V1 checks its original digest before a portable comparison. | [Fault result](validation/r96_stale_selected_attack.json) and [adversarial tests](tests/test_r96_evidence_repairs.py) |
| Inconsistent stored proof summaries | Reparse recorded output using the required theorem list and allowed axioms, compare detailed reports and axiom lines, derive model flags, and clear them on disagreement. | [Fresh 38-module gate](validation/r9_conditional_expectation_proof.json) and [aggregate](validation/r96_aggregate.json) |
| Missing installed manuscript | Wheel and Docker include four pinned TeX resources. Source admission hashes the contraction text through package resources and checks the vendored copy in a checkout. Damaging the installed resource produces an inconclusive outcome. | [Installed-wheel test](tests/test_r96_wheel.py), [Docker leaf](validation/r96_docker_leaf.stdout.log), [upstream byte checks](validation/r96_source_pin.json) |
| CI writing to sealed evidence | Verify the sealed checkout before regenerating evidence in a working copy. Upload changed evidence from that copy. The release verification script repeats the v08 mutation and rechecks the original manifest. | [Workflow](.github/workflows/test.yml) and [fresh-extraction verifier](scripts/verify_r96_release.py). Hosted Actions and branch protection were outside the local run. |
| Cross-build selected-point replay | Separate the portable mathematical digest from the artifact digest, while retaining interpreter and measurement metadata. | [3.12 write](validation/r96_selected_write.json) and [3.13 replay](validation/r96_selected_replay.stdout.log) |

## Finite recursion results

All six fixtures matched an independent direct contraction and factor elimination. The clausal fixtures also matched the repository's conventional DPLL model counter and count-DAG path. Each recursive certificate replayed against its original input. The timed algorithm received no direct parent value. Fixed seeds and inputs are in [the validation runner](scripts/validate_r96.py).

| Input | Wires | Result at stated precision | Outer recursive calls | Maximum depth |
|---|---:|---:|---:|---:|
| Satisfiable CNF with unused variable | 12 | 2 | 193 | 2 |
| Contradictory CNF with unused variable | 12 | 0 | 57 | 2 |
| Signed weighted cycle | 12 | 1,944,000 | 57 | 2 |
| Signed weighted cycle | 14 | 2,443,392 | 57 | 2 |
| Signed weighted cycle | 16 | 162,933,120 | 57 | 2 |
| Sixteen forced variables, boundary and Hermite pieces | 16 | 1 | 3 outer calls including both piece roots | 2 |

On the 16-wire forced-variable case the two Hermite pieces generated 24,592 child calls across 100 point evaluations. The hybrid took 28.56 s, with 117,342,208 bytes peak process RSS. Its fresh replay took 29.27 s. Conventional DPLL counting took approximately 0.000032 s on that fixture. On the signed 16-wire cycle, boundary recursion took 0.030 s, direct enumeration 0.327 s, and elimination 0.00023 s. These are single local measurements in separate worker processes, with possible background load. The timed region includes source binding for the certified algorithm. Machine evidence includes CPU time, replay time and memory per measurement. The system did not impose a memory ceiling on those runs. [Measurements and certificates](validation/r96_reductions.json)

The signed cycle results are residues modulo 2^41. In the CNF cases the n+1-bit root calculation determines the integer count uniquely. External Ganak, d4 and sharpSAT benchmarks were not run.

## Mathematical scope

- A new constructor returns one immutable executable group child per finite radix symbol, including the unit child for a vacant group. At the selected eight-wire point, six modes and 64 tuples give 256 group factors. The complete child sum equals the independent parent value `((169600000000,0,0,0,0),)` at p=521.
- A separate all-grid run verifies 26/26 points of a two-clause four-wire parent and 50/50 points of the forced eight-wire parent, then reconstructs counts 2 and 1 from the child outputs. Each direct comparison uses its own finite half-edge arithmetic. The eight-wire V3 transcript still records its original 0/50 in-transcript direct coverage. [New full-grid evidence](validation/r96_recipe_grid.json) · [V3 replay](validation/r96_8w_replay.stdout.log)
- The Lean kernel checked the distributive Boolean-boundary identity for arbitrary cut, left and right bit lengths and arbitrary signed integer functions at every p. The regression compiling a substitution with `True` requires the separately stated contract to fail. Table gathering, actual port membership and full executable correspondence remain outside that proof. [Audit and source mapping](docs/R96_REDUCTION_AUDIT.md)
- The point and Hermite experiments use bounded finite parameters. The 12–16-wire root algorithm uses Boolean boundary assignments. Manuscript-scheduled 64-group active recursion, universal executable refinement, the arbitrary-density outer reduction, and implementation bit-time and space bounds remain open.

## Local qualification

| Gate | Result |
|---|---|
| Python final full suite | 1421 passed in 334.57s (0:05:34), no skips |
| R9.6 focused regressions | 46 passed, including wheel install, CLI replay, altered proof contract and corrupted terms |
| Optimized-Python evidence and reduction cases | 43 passed under python -O, with the expected pytest warning on interpreter assertions |
| Lean 4.35.0 | 38 modules compiled and audited, 887 finite Lean/Python differential checks |
| Native scoring | C++20 self-test passed, 1,296 Python/C++ differential scores, 12 independent certificate replays |
| Inherited finite R9.5 validators | 160 entry equalities, 9 source-leaf counts, 258 interpolation checks |
| Inherited dense reconstruction | 579,584 / 4,033,536 / 24,813,568 counted scalar operations at 8 / 10 / 12 wires |
| Content binding | SHA-256 hashes with local unsigned compiler and executor |
| Hosted CI | Local workflow ordering and sealed release verification only |
| Complete source algorithm and complexity | BLOCKED, theorem execution disabled |

Command records, exit codes, interpreter versions, timings and memory reports under `validation/r96_*` distinguish newly executed evidence from historical releases.

## Reproduction

Run these commands from the extracted release directory. The exact native scoring test requires a C++20 compiler, Boost headers and CMake. The formal gate requires the compiler pinned in `lean-toolchain`.

```sh
python -m pip install -e '.[test,matching]' 'setuptools>=68' wheel pybind11
export PYTHONPATH=src
export LEAN_BIN="$(command -v lean)"
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
pyexe="$(python -c 'import sys; print(sys.executable)')"
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
  -DPYTHON_EXECUTABLE="$pyexe" -DPython_EXECUTABLE="$pyexe" -DPython3_EXECUTABLE="$pyexe"
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
python -m pytest -q -o addopts='' -rs
tmp="$(mktemp -d)"
python scripts/validate_conditional_expectation_lean.py --output "$tmp/proof.json"
python scripts/validate_r82.py --write "$tmp/selected.json"
python scripts/validate_r82.py --replay "$tmp/selected.json"
python scripts/validate_r96_recipe_grid.py --output "$tmp/grid.json"
python scripts/validate_r96.py --output "$tmp/reductions.json"
python scripts/validate_r91_cpp.py --output "$tmp/scoring.json"
printf 'p cnf 3 2\n1 2 0\n-1 2 0\n' > "$tmp/sample.cnf"
python -m veritas.research.finite_reductions "$tmp/sample.cnf" --leaf-edges 1 --write "$tmp/sample.json"
python -m veritas.research.finite_reductions "$tmp/sample.cnf" --leaf-edges 1 --replay "$tmp/sample.json"
```

The ZIP member-hash manifest, SHA-256 and fresh-extraction report are issued alongside the archive. Rebuild only from a disposable checkout after generating the desired evidence. Generated timing fields change the bytes of newly created evidence.

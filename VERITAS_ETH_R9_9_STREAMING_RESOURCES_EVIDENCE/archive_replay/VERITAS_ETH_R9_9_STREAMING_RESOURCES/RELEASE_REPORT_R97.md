# VERITAS-ETH R9.7 — paper verification and portable finite execution

This is a complete source distribution of a **partial mathematical implementation**.
It repairs finite portability and dense-boundary handling, adds a paper-linked
finite certificate checker, and strengthens the Lean boundary model. The general
OpenAI tensor algorithm, universal executable refinement and its complexity theorem
remain unimplemented/unproved. Theorem mode remains disabled.

## Input identity and preservation

Input: `VERITAS_ETH_R9_6_EVIDENCE_AND_RECURSION_PARTIAL_FULL_UPGRADED.zip`.
SHA-256: `2844ad664d57bc1a95b341c271ce062b7c311c56c975344515e978192e26970b`.
Fresh verification passed CRC, paths, regular-file policy, unique members, JSON
payload manifest, text manifest and `python -O` manifest checking. The archive has
919 members, 917 JSON payload hashes and 918 text hashes. The sealed-copy CI
exercise and extracted CLI replay also pass. See `validation/r97_input_archive.json`.
The original R9.6 ZIP and directory were preserved; R9.7 was assembled separately.

The four vendored LaTeX files were fetched from pinned commit
`4eaee87548250b2682affda7d05d947c05554bae` and compared byte-for-byte, with all
four matches recorded in `validation/r97_upstream_bytes.json`. Paper bytes are
unchanged. The mathematical audit identifies exact source labels and trust limits.

## Changes

* Added the `paper_verification` package: source registry, exact schedule,
  actual packing checks, independent boundary-tree consumer, complete finite
  child-sum consumer, rational Hermite checker and complete-grid evidence.
* Added an explicit `certified_elimination` option when the immediate boundary
  call lower bound exceeds policy. Strict mode continues to refuse. Every
  elimination table is independently recomputed before accepting a result.
* Made standalone wheels reproduce the checkout source identity using packaged
  immutable assets and actual installed bytes. Version/API metadata now agree on
  `3.8.2.post97` (engine 3.8.2, research checkpoint 97).
* Added general Lean table-gather, valid-partition contraction and contract modules,
  plus a concrete Python-to-Lean child-table fixture generator. The gate now has
  41 modules. The existing C++20 scorer and independent rational checker remain intact.
* Added 12/14/16-wire structural benchmarks and saved-grid corruption checks.
  CI includes these commands while preserving sealed input hashes and separate
  generated artifacts. Hosted CI and repository branch protection were not run.

## Fresh local results

Commands, exit codes, elapsed time, platform and measured RSS are in the referenced
JSON/log pairs. Tests executed are distinguished from compiler fixtures and oracle
comparisons; these counts must not be summed into a theorem-completion percentage.

| Check | Executed outcome | Evidence |
|---|---|---|
| Full Python suite, pinned Lean available | **1,456 passed**, no skips, 380.01 s pytest / 381.29 s command | `validation/r97_full_final.*` |
| Lean gate | **41/41 modules** compiled and audited, exit 0, 44.79 s | `r97_lean.*`, `r9_conditional_expectation_proof.json` |
| Concrete child-table/port bridge | **16 kernel-checked fixtures**; changed table rejected | `r97_concrete_bridge.json`, `r97_rejected_table.json` |
| Existing Lean/Python ordering/domain comparisons | **887/887** | `r97_order_differential.json` |
| Exact C++ scorer | Native build/self-test pass, **1,296 comparisons**, **12 independent certificate replays** | `r97_cpp*` |
| New paper-linked 64-group grid | **116/116 points**, 452 tuples, 28,928 group values, result `(2,0,0,0,0)` | `r97_grid.json`, `r97_grid_write.*`, `r97_grid_verify.*` |
| Cross-Python grid replay | Python **3.13.13** accepts Python **3.12.0** record | `r97_py313_grid.*` |
| Saved-grid adversarial CLI checks | **8/8 rejected without result** under `python -O` | `r97_grid_faults.json` |
| Optimized-Python focused tests | **35 passed, 1 compiler-dependent skip**, one pytest warning about optimized assertions | `r97_optimized_faults.*` |
| Original R96 finite recipe grids | **76/76 points**, exact four/eight-wire recoveries | `r97_scaled_r96_grid.json` |
| New structural matrix | **15/15** exact results/replays across 12, 14 and 16 wires | `r97_matrix.json` |
| Original R96 reductions | Six networks and three selected points pass | `r97_inherited_reductions.json` |
| Original eight-wire V3 | Fresh write and replay pass; 12,297 calls, depth 1, 3,074 tuples | `r97_eight_wire_v3.json`, `r97_v3_*` |
| Clean installed wheel | Signed one-wire result 7, checkout-certificate replay, source leaf and mutation refusals pass in full suite | `tests/test_r96_wheel.py` |
| Linux installed-package Docker check | Signed result 7, dense result 65,536, source pin and independent tree pass | `r97_docker_execution.*` |
| Freshness aggregator | Pass; universal Python/C++ refinement flags remain false | `r97_proof_aggregate_final.json` |

The full suite includes the new negative test that replaces the nontrivial Lean
partition theorem with `True`; its dependent contract fails compilation. The
optimized-Python subset's unavailable compiler test was executed in the full suite.
The first development full run recorded one replay failure during concurrent
source edits (1,453 passed, one failed). After source freeze that test passed in
isolation and the complete 1,456-case run passed. Both logs remain, without
retroactively marking the earlier run successful. An initial grid JSON replay
also exposed a list/tuple normalization defect; the final checker explicitly
validates and normalizes exponent-vector containers and its JSON regression passes.

Mac verification used Python 3.12.0, macOS 26.2 ARM64, Lean 4.35.0 commit
`eb6cafb7290e8bd5f2937522d8d804f58f02bafc`, and the local C++20 toolchain. Docker
used Linux ARM64, Python 3.12.14, `--network none --memory=512m --cpus=1` and an
installed package from `/tmp`. Its process peak RSS was 27,275,264 bytes. This
memory limit applies to that container run; most other checks use cooperative caps.

## What the results establish

The dense two-factor obstruction is handled by an explicitly recorded ordinary
elimination algorithm. Strict mode detects its call-budget obstruction before
materializing the boundary tree. The fallback's exactness is checked at every
bucket. This expands finite support without claiming universal 16-wire completion
under all resource policies.

The 64-group experiment checks finite coefficient preservation and reconstruction.
Its source schedule has `u_0=0`; it uses declared scaled parameters. Its largest
child is four wires, the same as its parent. Thus it does not certify the source
packing regime, source shrinking, or multilevel source execution. The old eight-wire
V3 transcript still has zero directly checked active points out of 50 internally;
separate complete-grid evidence must not rewrite that transcript's coverage.

Performance remains mixed. In the structural matrix the signed 16-wire cycle took
about 29.3 ms through checked boundary execution, 0.30 ms through ordinary factor
elimination and 239.1 ms through direct enumeration. The dense 16-wire certified
path took about 650.2 ms, compared with 280.8 ms ordinary elimination and 193.1 ms
direct enumeration. These are single-machine local measurements with explicit
checking overhead, not a practical #SAT speedup or an asymptotic claim.

| Qualification | Status | Remaining dependency |
|---|---|---|
| Source identity and finite parameter correspondence | PASS within documented bounds | General TeX-to-code semantic proof |
| Python finite tests / C++ finite differential checks | PASS | Universal executable refinement |
| Complete selected finite grids / negative tests | PASS | All source instances and recursive depths |
| Lean boundary/gather/partition model | KERNEL-CHECKED | Arbitrary executable reindexing and recursion bridge |
| Portable wheel and local Docker | PASS | Hosted platform/CI qualification |
| Resource measurements | RECORDED | Complete bit-work and peak-space proof |
| Source-defined active recursion | BLOCKED | Universal modes, children, precision and shrinkage composition |
| Complexity and arbitrary-density reduction | BLOCKED | Complete algorithm and corresponding proof |
| Theorem mode | DISABLED | Full proof-to-executable chain |

## Reproduce from a fresh extraction

Run the sealed manifest check before generating new evidence. To keep the sealed
payload unchanged, copy the tree to a work directory and run these commands there.
Use separate fresh output names if preserving historical logs matters.

```sh
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
python -m pip install -e '.[test]' pybind11
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
  -DPYTHON_EXECUTABLE="$(command -v python)" \
  -DPython_EXECUTABLE="$(command -v python)" \
  -DPython3_EXECUTABLE="$(command -v python)"
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
# Install the toolchain specified in lean-toolchain; LEAN_BIN can select it explicitly.
lean --version
python scripts/validate_conditional_expectation_lean.py --output validation/fresh_proof.json
PYTHONPATH=src python -m pytest -q -o addopts=''
python scripts/validate_r97_bridge.py --output validation/fresh_bridge.json
python scripts/validate_r97_paper.py --write validation/fresh_grid.json
python scripts/validate_r97_paper.py --verify validation/fresh_grid.json
python scripts/validate_r97_grid_faults.py validation/fresh_grid.json --output validation/fresh_faults.json
python scripts/validate_r97_matrix.py --output validation/fresh_matrix.json
python scripts/validate_r91_cpp.py --output validation/fresh_cpp.json
python scripts/validate_r94_foundation.py --output validation/fresh_order.json
python scripts/validate_r95_recipes.py --output validation/fresh_recipes.json
python scripts/validate_r96_recipe_grid.py --output validation/fresh_r96_grid.json
python scripts/validate_r96.py --output validation/fresh_reductions.json
python scripts/validate_tapered_v4.py --write validation/fresh_v3.json
python scripts/validate_tapered_v4.py --replay validation/fresh_v3.json
python scripts/seal_wheel_sources.py
python -m pip wheel --no-deps --no-build-isolation -w ../wheelhouse .
python scripts/build_release.py --output-name VERITAS_ETH_R9_7_PAPER_VERIFICATION_PARTIAL_FULL_UPGRADED.zip
python scripts/verify_manifest.py
```

The release ZIP's `.manifest.json`, `.sha256` and `.verification.json` sidecars
bind its final bytes and the fresh-extraction check without a self-referential
archive hash. Compiler binaries, native build outputs and caches are excluded.
The Python wheel is a separate portable artifact; the ZIP contains the C++ source
and reproducible build configuration. See `docs/R97_FINITE_EXECUTION.md` for the
installed-package and routing contracts, and `docs/R97_PAPER_CONFORMANCE_AUDIT.md`
for the precise proof boundary.

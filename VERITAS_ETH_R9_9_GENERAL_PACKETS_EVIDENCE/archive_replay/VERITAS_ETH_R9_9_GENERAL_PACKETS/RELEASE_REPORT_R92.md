# VERITAS-ETH R9.2 packet-address partial release

## Release scope

This is a partial R9.2 implementation. It adds a finite global packet-address
codec and checker, plus Lean proofs of canonical symbol-pair
pattern/orientation reconstruction and pattern/copy/orientation slot-word
inverses. It does not complete the source-to-executable bijection or R9.3/R9.4.

The theorem recursion remains guarded by
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`. No universal packing,
parent-to-child identity, recursive recovery, complexity, polynomial-space,
or ETH theorem claim is enabled.

## Implemented and checked

| Area | Evidence | Status |
|---|---|---|
| R9.2 finite packet address codec | `tests/test_r92_global_packet_bijection.py` plus implicit-packet regressions; 53 passed | `PYTHON_TESTED` |
| Independent bounded address oracle | Exhaustive directed-class/offset and canonical pattern/packet/slot enumeration under explicit caps | `FINITE_CHECKER_TESTED` |
| Lean canonical address model | `validation/r9_2_packet_lean.json`; pinned Lean 4.35.0; 23 modules; exact axiom reports passed | `LEAN_KERNEL_CHECKED` |
| Source offset-to-copy-bit composition | Not yet formalized as a single theorem | `OPEN` |
| Python/C++ builder refinement | Bounded differential checks only; no source-level refinement theorem | `NOT_PROVED` |
| Recursive contraction and Hermite composition | No new implementation in this release | `NOT_IMPLEMENTED` |
| Bit-time and peak-space proof | No complete recurrence for the executable | `COMPLEXITY_NOT_ESTABLISHED` |
| Theorem mode | Explicitly fail-closed | `DISABLED` |

## Reproduction

```bash
PYTHONPATH=src python -m pytest -q -o addopts='' \
  tests/test_r92_global_packet_bijection.py \
  tests/test_d3_implicit.py \
  tests/test_sparse_packet_source_equivalence.py

python scripts/validate_conditional_expectation_lean.py \
  --output validation/r9_2_packet_lean.json

cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
./build/cpp/veritas_d3_selftest
PYTHONPATH=src python -m pytest -q -o addopts=''
python scripts/build_release.py \
  --output-name VERITAS_ETH_R9_2_PACKET_ADDRESS_PARTIAL_FULL_UPGRADED.zip
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

The post-integration focused packet/downstream run passed 72 tests in
1.58 seconds. The pre-follow-up full suite passed 1,210 tests in 137.07
seconds on Python 3.12.0 / macOS 26.2 arm64. The additional R9.2.1 work and
fresh validation are recorded below.

## R9.2.1 follow-up: evidence freshness and streaming pair storage

The aggregate release validator now rejects a saved Lean `PASS` unless every
current proof source hash, the exact 23-module inventory, the pinned manuscript
and toolchain, the current Lean-validator hash, central theorem reports, and
axiom audits still match. Formal flags are derived from their named proof
outputs rather than inferred from the aggregate pass. The result is labelled
`PASS_HASH_MATCH_UNAUTHENTICATED`: hashes detect stale inputs but do not sign
the evidence or authenticate the Lean binary. The adversarial freshness tests
cover source edits and deletions, altered report inventory, manuscript and
toolchain changes, validator edits, and invalid axiom reports.

The C++ batch scorer no longer stores incident and independent edge-pair
vectors. It streams pairs in deterministic `(i,j)` order with an O(M) byte
mask and edge-index list, preserving exact scores and the V4 work metric. Its
native self-test checks a 1,000-edge case (499,500 unordered pairs) against
the direct scorer for each candidate. This establishes a linear pair-index
scratch representation; no OS-enforced memory measurement or full
peak-memory/bit-complexity bound is claimed.

Fresh local validation on Python 3.12.0 / macOS 26.2 arm64:

| Check | Result |
|---|---|
| Full Python suite | 1,216 passed in 146.74 seconds |
| New Lean gate | 23 modules passed on Lean 4.35.0 in 36.297051 seconds; manuscript pin `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860` |
| Release aggregate | `PASS_R91_FINITE_AND_FORMAL_MODEL_GATES`; Lean freshness `PASS_HASH_MATCH_UNAUTHENTICATED` |
| C++ CMake build and self-test | Passed, including the 1,000-edge streamed batch case |
| C++ differential | 1,296 candidate-score cases; 12 independent rational certificate replays; exact finite results |
| C++ benchmark | Five small/medium workloads; all score tables and direct work metrics matched. Measurements remain workload-specific |
| CNF-to-tensor finite path | Included in the 1,216-test suite; exact counts and independent structure/oracle checks passed on bounded fixtures |

Evidence files: `validation/r9_conditional_expectation_proof.json`,
`validation/r9_1_differential.json`, `validation/r91_benchmarks.json`, and
`validation/r9_2_release_evidence.json`. Reproduction commands:

```bash
lean --version
python scripts/validate_conditional_expectation_lean.py \
  --output validation/r9_conditional_expectation_proof.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/validate_r91.py --output validation/r9_2_release_evidence.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/validate_r91_cpp.py --output validation/r9_1_differential.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/benchmark_r91_scorer.py --output validation/r91_benchmarks.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python -m pytest -q -o addopts=''
```

The proof gate's universal packing, full padded-offset composition, executable
Python/C++ refinement, recursive child correctness, complete resource bound,
and theorem-mode qualifications remain false or open. The theorem branch is
still fail-closed.

The next dependency is a Lean binary-word/value equivalence composed with
class offset quotient/remainder, followed by proof that the deterministic
Python/C++ packet builder implements that exact map. Only after that can the
R9.2 global acceptance gate be considered.

# R9.1 C++20 scorer design

## Scope and ABI

Python remains the orchestrator and the default reference implementation. The
native code implements the exact D.3 candidate score and a batched one-vertex
step. It does not choose labels, construct packets, or prove the manuscript's
packing lemma. The independent rational certificate checker does not call
either C++ entry point.

`cpp/include/veritas_d3_score.h` exposes two caller-buffer C ABI functions:

* `veritas_d3_candidate_score` computes one candidate score as an exact
  `boost::multiprecision::cpp_int`, returned as decimal text;
* `veritas_d3_vertex_scores` computes every label in
  `itertools.product(range(r), repeat=a)` order, plus the parent average.

An optional pybind11 module exposes the same operations. The C ABI and ctypes
path remain available when pybind11 is absent. The pybind wrappers check
sequence lengths before converting them to bounded C++ vectors. The ABI itself
uses caller-owned buffers; callers must supply valid buffers of the declared
capacity.

The selected path is recorded as `python`, `cpp-pybind`, or `cpp-ctypes` in the
certificate. `score_backend="cpp"` fails if native code cannot be loaded;
`score_backend="auto"` may fall back to Python and records that selection.

## Score and exactness

For `M` indexed edge occurrences and `D=r^(2a)`, the candidate score is

`M*D + sum_{unordered edge-index pairs} 2*(D/r^u)`

for pairs still capable of colliding, where `u` is the number of unresolved
side-coordinate equalities; a known mismatch contributes zero. Repeated edge
occurrences remain distinct. Row and column endpoints with the same numeric ID
remain different vertices. The division is exact because `u <= 2a`.

The batch scorer separates pairs that touch the current vertex from pairs that
do not. It evaluates the candidate-independent contribution once, then adds
the candidate-dependent incident-pair contribution for each word. It streams
those pair sets in the original `(i, j)` order and stores only an `M`-byte
incidence mask and at most `M` edge indices, so its pair-selection scratch is
`O(M)`, not `O(M^2)`. The parent score is evaluated independently by the
corresponding exact averaging rule.
Python checks that it equals the preceding conditional expectation and checks
that the full candidate-score sum has the required average.

Both score values and class powers use arbitrary-precision integers. ABI
dimensions and symbols are range-checked; there are no floating-point score
comparisons or lossy integer conversions.

## Work metrics and resource guards

The V3 direct metric is preserved as
`d3-direct-pair-score-work-v1`: pair visits, coordinate comparisons and
candidate bookkeeping. The optimized V4 metric is
`d3-batch-pair-score-work-v1`: pair classifications, exact pair-score visits,
coordinate comparisons and candidate bookkeeping. V4 certificates bind the
metric version in both policy and resource ledger. The independent checker
recomputes the V4 count with separate Python loops and rationally recomputes
the scores; it does not compare unlike V3/V4 counters as if they were equal.

The native implementation fails closed at these caps: radix and dimension at
most 64, 100,000 edge occurrences, 10,000 distinct vertices per side, 100,000
candidate labels per batch, 1,000,000 unordered-pair evaluations, 64 MiB of
batch score output, and at most 100,000,000 conservative batch work units per
whole build. Pair evaluation work is capped; pair records are not retained.
Direct calls also have explicit pair and work caps. An explicit zero
work budget is zero; `UINT64_MAX` is reserved for the internal unlimited
sentinel. No result is returned on a budget failure.

The 1,000-edge self-test exercises 499,500 unordered pairs and checks every
batch candidate against the direct scorer. The linear scratch property follows
from the concrete mask/index representation; this test is not a peak-RSS
measurement. These are operational bounds, not a bit-complexity or full
peak-memory proof.

## Building and validation

Requirements: CMake 3.20+, a C++20 compiler, and Boost headers. pybind11 is
optional. Build and test the C ABI with:

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
ctest --test-dir build/cpp --output-on-failure
```

To include pybind11, install it for the selected Python and pass its CMake
directory as `-Dpybind11_DIR=...`. Linux, macOS and MSVC configurations are
provided; only the platforms actually built in validation evidence count as
tested.

Run finite validation with:

```sh
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/validate_r91_cpp.py --output validation/r9_1_differential.json
PYTHONPATH=src VERITAS_D3_CPP_BUILD_DIR="$PWD/build/cpp" \
  python scripts/benchmark_r91_scorer.py --output validation/r91_benchmarks.json
```

The current differential evidence checks 1,296 candidate-score/state pairs,
12 fixture executions across the pybind11 and ctypes transports, large
integers, and 12 independent rational certificate replays. The benchmark
compares Python reference, C++ direct, and C++ batch on five identical finite
score tables with three repeats each. Timings and process RSS are
measurements, not guarantees; RSS is not an OS-enforced limit. Python/C++
agreement and finite replay do not prove executable refinement or the
universal theorem. Reproduction details and exact evidence paths are in
`RELEASE_REPORT_R91.md`.

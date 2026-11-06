# R9.1 C++20 scoring backend

## Scope

The C++ backend ports the exact candidate score and adds a batched evaluator
for all labels at one vertex. It does not rewrite the solver or construct
packets, and is not formally verified. Lean verification and the C++ runtime
are deliberately separate: matching outputs on a test corpus is evidence, not
a proof.

## Layout

```
cpp/
  CMakeLists.txt        # C ABI library (always), pybind11 module (optional), self-test
  include/veritas_d3_score.h
  src/score.cpp         # exact scorer + vertex-step batch
  src/bindings.cpp      # pybind11 module `veritas_d3`
  tests/selftest.cpp    # dependency-free fixture check
```

## Entry points

* `veritas_d3_candidate_score` — one candidate label, exact
  `boost::multiprecision::cpp_int` result returned as a decimal string.
* `veritas_d3_vertex_scores` — every `r**a` candidate label for one vertex
  step, in the same order as `itertools.product(range(r), repeat=a)`, plus the
  exact candidate average (`concreteD3ScoreParent`).
* `veritas_d3` (pybind11) — the same two operations with native Python types.

## Exactness

* Scores are arbitrary-precision integers. The C ABI returns decimal text so
  no conversion can round; the bindings return `str` for the same reason.
* `D // r**unknown` is exact because `unknown <= 2*a`, so the C++ division and
  the Python floor division agree for every reachable state.
* Every candidate is enumerated with the first coordinate most significant,
  which is CPython's `product` order.

## Validation and budgets

* Vertex ids must be non-negative and strictly ascending per side.
* Assignment tables use `-1` for unassigned; symbols must lie in `[0, r)`.
* Hard limits: `edge_count <= 100000`, `dimension <= 64`, `radix <= 64`, at
  most 10000 vertices per side, 100000 candidate labels per batch, 1000000
  unordered pair records, 64 MiB of batch output, and 100000000 conservative
  native batch work units per complete build.
* V3 direct work units are versioned as
  `d3-direct-pair-score-work-v1`: pair visits, coordinate comparisons and
  candidate bookkeeping. V4 batch units are versioned as
  `d3-batch-pair-score-work-v1`: pair classifications, pair-score visits,
  coordinate comparisons and candidate bookkeeping. The independent V4
  certificate checker recomputes the latter with separately written loops.
  The two metrics are intentionally not compared as equal.
* Budget exhaustion, counter overflow, and undersized output buffers are
  reported as distinct status codes and mapped to `PackingBudgetExceeded`,
  `OverflowError`, and `BufferError`.

## Python integration

`cpp_backend.resolve_score_backend("python" | "cpp" | "auto")` returns
`("python", None)`, `("cpp-pybind", module)`, or
`("cpp-ctypes", (library, candidate_fn, batch_fn))`. `auto` prefers pybind11,
then ctypes, then the pure-Python scorer. `cpp` raises
`CppBackendUnavailable` rather than falling back, so a requested native path
is never silently replaced.

`streaming.construct_streaming_d3_packing(..., score_backend=...)` records
`score_backend`, `score_backend_requested`, `algorithm_version`, and (for V4)
the batch work-metric version in the certificate and resource ledger.

## Building

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release \
      -Dpybind11_DIR=$(python3 -c 'import pybind11; print(pybind11.get_cmake_dir())') \
      -DPYTHON_EXECUTABLE=$(which python3) \
      -DPython_EXECUTABLE=$(which python3) \
      -DPython3_EXECUTABLE=$(which python3)
cmake --build build/cpp -j
./build/cpp/veritas_d3_selftest
```

Boost headers are required. pybind11 is optional: without it the C ABI library
still builds and the ctypes path is used. On Windows the same CMake project
builds with MSVC; the exported symbols use `__declspec(dllexport)`. On Linux
and macOS the default visibility is hidden and only the C ABI symbols are
exported.

## Performance

`scripts/benchmark_r91_scorer.py` measures the Python reference, the C++
direct path, and the C++ batch path on identical inputs. Batch scoring can
reduce repeated work when many pairs do not touch the current vertex, but
incident pairs may still be quadratic in `M`; no general worst-case speedup
is claimed. See `validation/r91_benchmarks.json` and
`docs/R91_COMPLEXITY.md`.

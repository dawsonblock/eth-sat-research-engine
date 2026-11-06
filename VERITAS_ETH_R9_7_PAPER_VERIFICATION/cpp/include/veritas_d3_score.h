#pragma once

#include <cstddef>
#include <cstdint>

#if defined(_WIN32)
#  if defined(VERITAS_D3_SCORE_BUILD)
#    define VERITAS_D3_API __declspec(dllexport)
#  else
#    define VERITAS_D3_API __declspec(dllimport)
#  endif
#else
#  define VERITAS_D3_API __attribute__((visibility("default")))
#endif

/// Status codes shared by the C ABI and the Python bindings.
enum VeritasD3Status : int {
  VERITAS_D3_OK = 0,
  VERITAS_D3_INVALID_INPUT = 1,
  VERITAS_D3_BUDGET_EXCEEDED = 2,
  VERITAS_D3_COUNTER_OVERFLOW = 3,
  VERITAS_D3_OUTPUT_TOO_SMALL = 4,
};

extern "C" {

/// Evaluate `_candidate_score` for one candidate label.
///
/// `row_vertex_ids`/`column_vertex_ids` must be strictly ascending.  The
/// assignment tables hold `dimension` entries per vertex with `-1` meaning
/// unassigned.  `score_output` receives the decimal value of an exact
/// arbitrary-precision integer.
VERITAS_D3_API int veritas_d3_candidate_score(
    std::uint64_t radix,
    std::uint64_t dimension,
    std::size_t edge_count,
    const std::int64_t* edge_rows,
    const std::int64_t* edge_columns,
    std::size_t row_vertex_count,
    const std::int64_t* row_vertex_ids,
    const std::int16_t* row_assignments,
    std::size_t column_vertex_count,
    const std::int64_t* column_vertex_ids,
    const std::int16_t* column_assignments,
    std::uint32_t current_side,
    std::int64_t current_vertex,
    const std::uint32_t* candidate,
    std::uint64_t work_budget,
    char* score_output,
    std::size_t score_output_capacity,
    std::uint64_t* work_output,
    char* error_output,
    std::size_t error_output_capacity);

/// Evaluate every candidate label for one vertex step.
///
/// Scores are written in the same order as Python's
/// `itertools.product(range(radix), repeat=dimension)`: the first coordinate
/// is the most significant digit.  `score_output` must hold
/// `radix**dimension` integers of `score_stride` bytes each (decimal, NUL
/// terminated).  `parent_output` receives `concreteD3ScoreParent`.
///
/// `work_output` reports the units this routine charged.  The accounting
/// rules are the same as `streaming.py` (one unit per pair visit, per
/// coordinate comparison, and per candidate), but a vertex step that avoids
/// re-scanning candidate-independent pairs legitimately charges fewer units
/// than the direct loop.  Callers that need the direct-loop count must use
/// `veritas_d3_candidate_score` for every candidate.
VERITAS_D3_API int veritas_d3_vertex_scores(
    std::uint64_t radix,
    std::uint64_t dimension,
    std::size_t edge_count,
    const std::int64_t* edge_rows,
    const std::int64_t* edge_columns,
    std::size_t row_vertex_count,
    const std::int64_t* row_vertex_ids,
    const std::int16_t* row_assignments,
    std::size_t column_vertex_count,
    const std::int64_t* column_vertex_ids,
    const std::int16_t* column_assignments,
    std::uint32_t current_side,
    std::int64_t current_vertex,
    std::uint64_t candidate_count,
    char* score_output,
    std::size_t score_stride,
    char* parent_output,
    std::size_t parent_output_capacity,
    std::uint64_t work_budget,
    std::uint64_t* work_output,
    char* error_output,
    std::size_t error_output_capacity);

/// The algorithm identifier reported by the bindings.
VERITAS_D3_API const char* veritas_d3_algorithm_version(void);

}  // extern "C"

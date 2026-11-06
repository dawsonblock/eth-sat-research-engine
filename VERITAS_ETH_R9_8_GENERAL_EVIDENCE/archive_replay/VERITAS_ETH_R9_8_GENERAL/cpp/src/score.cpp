#include "veritas_d3_score.h"

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>

namespace {

using boost::multiprecision::cpp_int;

constexpr std::size_t kMaximumEdges = 100000;
constexpr std::size_t kMaximumVerticesPerSide = 10000;
constexpr std::uint64_t kMaximumBatchCandidates = 100000;
constexpr std::uint64_t kMaximumBatchPairs = 1000000;
constexpr std::uint64_t kMaximumDirectPairs = 1000000;
constexpr std::uint64_t kMaximumDirectWork = 100000000;
constexpr std::uint64_t kMaximumBatchWork = 100000000;
constexpr std::size_t kMaximumBatchOutputBytes = 64 * 1024 * 1024;
constexpr std::uint64_t kUnlimited = std::numeric_limits<std::uint64_t>::max();
constexpr const char* kAlgorithmVersion = "d3-cpp20-direct-v1+batch-v1";

struct BudgetExceeded final : std::exception {};
struct CounterOverflow final : std::exception {};

void write_text(char* output, std::size_t capacity, const std::string& value) {
  if (output == nullptr || capacity == 0) return;
  const auto length = std::min(capacity - 1, value.size());
  std::memcpy(output, value.data(), length);
  output[length] = '\0';
}

cpp_int integer_power(std::uint64_t base, std::uint64_t exponent) {
  cpp_int result = 1;
  for (std::uint64_t i = 0; i < exponent; ++i) result *= base;
  return result;
}

/// A read-only view of the scorer inputs with a validated vertex index.
struct Layout {
  std::uint64_t radix;
  std::uint64_t dimension;
  std::size_t edge_count;
  const std::int64_t* edge_rows;
  const std::int64_t* edge_columns;
  std::size_t row_vertex_count;
  const std::int64_t* row_vertex_ids;
  const std::int16_t* row_assignments;
  std::size_t column_vertex_count;
  const std::int64_t* column_vertex_ids;
  const std::int16_t* column_assignments;

  std::size_t index(std::uint32_t side, std::int64_t vertex) const {
    const std::int64_t* ids = side == 0 ? row_vertex_ids : column_vertex_ids;
    const std::size_t count = side == 0 ? row_vertex_count : column_vertex_count;
    if (count == 0 || ids == nullptr) {
      throw std::invalid_argument("vertex side table is empty");
    }
    const auto found = std::lower_bound(ids, ids + count, vertex);
    if (found == ids + count || *found != vertex) {
      throw std::invalid_argument("edge endpoint is absent from its side table");
    }
    return static_cast<std::size_t>(found - ids);
  }

  std::int16_t recorded(std::uint32_t side, std::int64_t vertex,
                        std::uint64_t coordinate) const {
    const std::int16_t* assignments = side == 0 ? row_assignments : column_assignments;
    return assignments[index(side, vertex) * dimension + coordinate];
  }
};

bool valid_ids(const std::int64_t* ids, std::size_t count) {
  if (count > kMaximumVerticesPerSide || (count > 0 && ids == nullptr)) return false;
  for (std::size_t i = 0; i < count; ++i) {
    if (ids[i] < 0 || (i > 0 && ids[i - 1] >= ids[i])) return false;
  }
  return true;
}

bool valid_assignments(const std::int16_t* values, std::size_t count,
                       std::uint64_t radix) {
  if (count > 0 && values == nullptr) return false;
  for (std::size_t i = 0; i < count; ++i) {
    if (values[i] < -1 || values[i] >= static_cast<std::int16_t>(radix)) return false;
  }
  return true;
}

/// The `value(side, ident, coordinate)` closure from `_candidate_score`.
struct Values {
  const Layout& layout;
  std::uint32_t current_side;   // 0 row, 1 column, 2 none
  std::int64_t current_vertex;
  const std::uint32_t* candidate;  // may be null for the parent evaluation

  bool is_current(std::uint32_t side, std::int64_t vertex) const {
    return current_side < 2 && side == current_side && vertex == current_vertex;
  }

  std::int16_t at(std::uint32_t side, std::int64_t vertex, std::uint64_t coordinate) const {
    if (is_current(side, vertex)) {
      return candidate == nullptr ? -1
                                  : static_cast<std::int16_t>(candidate[coordinate]);
    }
    return layout.recorded(side, vertex, coordinate);
  }
};

/// The exact `_candidate_score` pair term for one unordered edge pair.
///
/// Returns `2 * (D // radix**unknown)` when the pair can still agree and `0`
/// when a known coordinate already disagrees.  `charged` receives the work
/// units the reference loop charges for this pair (one for the pair visit
/// plus one per executed coordinate comparison).
cpp_int pair_term(const Values& values, std::uint64_t radix, std::uint64_t dimension,
                  const cpp_int& classes, std::int64_t row_a, std::int64_t col_a,
                  std::int64_t row_b, std::int64_t col_b, std::uint64_t& charged) {
  ++charged;  // pair visit
  std::uint64_t unknown = 0;
  for (std::uint64_t d = 0; d < dimension; ++d) {
    const std::int64_t left[2] = {row_a, col_a};
    const std::int64_t right[2] = {row_b, col_b};
    for (std::uint32_t side = 0; side < 2; ++side) {
      if (left[side] == right[side]) continue;
      ++charged;  // coordinate comparison
      const std::int16_t x = values.at(side, left[side], d);
      const std::int16_t y = values.at(side, right[side], d);
      if (x >= 0 && y >= 0) {
        if (x != y) return 0;
      } else {
        ++unknown;
      }
    }
  }
  return 2 * (classes / integer_power(radix, unknown));
}

/// The parent score term: the exact average of the candidate terms over the
/// `radix**dimension` labels of the current vertex.
///
/// A comparison that involves the current vertex always contributes exactly
/// one unknown: either the current symbol is free and the other endpoint is
/// known, or both are free, in which case the candidate average is `2*D/radix`.
/// This mirrors `pairTermParent` in the Lean development.
cpp_int parent_pair_term(const Layout& layout, std::uint32_t current_side,
                         std::int64_t current_vertex, std::uint64_t radix,
                         std::uint64_t dimension, const cpp_int& classes,
                         std::int64_t row_a, std::int64_t col_a, std::int64_t row_b,
                         std::int64_t col_b, std::uint64_t& charged) {
  ++charged;
  std::uint64_t unknown = 0;
  for (std::uint64_t d = 0; d < dimension; ++d) {
    const std::int64_t left[2] = {row_a, col_a};
    const std::int64_t right[2] = {row_b, col_b};
    for (std::uint32_t side = 0; side < 2; ++side) {
      if (left[side] == right[side]) continue;
      ++charged;
      const bool left_current =
          current_side < 2 && side == current_side && left[side] == current_vertex;
      const bool right_current =
          current_side < 2 && side == current_side && right[side] == current_vertex;
      if (left_current || right_current) {
        ++unknown;
        continue;
      }
      const std::int16_t x = layout.recorded(side, left[side], d);
      const std::int16_t y = layout.recorded(side, right[side], d);
      if (x >= 0 && y >= 0) {
        if (x != y) return 0;
      } else {
        ++unknown;
      }
    }
  }
  return 2 * (classes / integer_power(radix, unknown));
}

struct Request {
  std::uint64_t radix;
  std::uint64_t dimension;
  std::size_t edge_count;
  const std::int64_t* edge_rows;
  const std::int64_t* edge_columns;
  std::size_t row_vertex_count;
  const std::int64_t* row_vertex_ids;
  const std::int16_t* row_assignments;
  std::size_t column_vertex_count;
  const std::int64_t* column_vertex_ids;
  const std::int16_t* column_assignments;
  std::uint32_t current_side;
  std::int64_t current_vertex;
};

Layout validate(const Request& request, const std::uint32_t* candidate,
                bool require_candidate) {
  if (request.radix < 2 || request.radix > 64 || request.dimension == 0 ||
      request.dimension > 64 || request.edge_count > kMaximumEdges ||
      request.current_side > 2 ||
      (request.current_side < 2 && request.current_vertex < 0) ||
      !valid_ids(request.row_vertex_ids, request.row_vertex_count) ||
      !valid_ids(request.column_vertex_ids, request.column_vertex_count) ||
      !valid_assignments(request.row_assignments,
                         request.row_vertex_count * request.dimension, request.radix) ||
      !valid_assignments(request.column_assignments,
                         request.column_vertex_count * request.dimension, request.radix) ||
      (request.edge_count > 0 && (request.edge_rows == nullptr ||
                                  request.edge_columns == nullptr))) {
    throw std::invalid_argument("invalid scorer input or explicit resource cap exceeded");
  }
  if (require_candidate) {
    if (candidate == nullptr) throw std::invalid_argument("missing candidate label");
    for (std::uint64_t d = 0; d < request.dimension; ++d) {
      if (candidate[d] >= request.radix) {
        throw std::invalid_argument("candidate symbol outside radix");
      }
    }
  }
  Layout layout{request.radix, request.dimension, request.edge_count, request.edge_rows,
                request.edge_columns, request.row_vertex_count, request.row_vertex_ids,
                request.row_assignments, request.column_vertex_count,
                request.column_vertex_ids, request.column_assignments};
  for (std::size_t i = 0; i < request.edge_count; ++i) {
    if (request.edge_rows[i] < 0 || request.edge_columns[i] < 0) {
      throw std::invalid_argument("invalid edge endpoint");
    }
    layout.index(0, request.edge_rows[i]);
    layout.index(1, request.edge_columns[i]);
  }
  if (request.current_side < 2) layout.index(request.current_side, request.current_vertex);
  return layout;
}

struct Work {
  std::uint64_t budget;
  std::uint64_t used = 0;
  void add(std::uint64_t amount) {
    if (used > kUnlimited - amount) throw CounterOverflow{};
    used += amount;
    if (budget != kUnlimited && used > budget) throw BudgetExceeded{};
  }
};

}  // namespace

extern "C" const char* veritas_d3_algorithm_version() { return kAlgorithmVersion; }

extern "C" int veritas_d3_candidate_score(
    std::uint64_t radix, std::uint64_t dimension, std::size_t edge_count,
    const std::int64_t* edge_rows, const std::int64_t* edge_columns,
    std::size_t row_vertex_count, const std::int64_t* row_vertex_ids,
    const std::int16_t* row_assignments, std::size_t column_vertex_count,
    const std::int64_t* column_vertex_ids, const std::int16_t* column_assignments,
    std::uint32_t current_side, std::int64_t current_vertex,
    const std::uint32_t* candidate, std::uint64_t work_budget, char* score_output,
    std::size_t score_output_capacity, std::uint64_t* work_output, char* error_output,
    std::size_t error_output_capacity) {
  if (work_output != nullptr) *work_output = 0;
  if (score_output != nullptr && score_output_capacity > 0) score_output[0] = '\0';
  if (error_output != nullptr && error_output_capacity > 0) error_output[0] = '\0';
  try {
    Request request{radix, dimension, edge_count, edge_rows, edge_columns,
                    row_vertex_count, row_vertex_ids, row_assignments,
                    column_vertex_count, column_vertex_ids, column_assignments,
                    current_side, current_vertex};
    const Layout layout = validate(request, candidate, true);
    const std::uint64_t pair_count =
        static_cast<std::uint64_t>(edge_count) *
        (edge_count - (edge_count > 0 ? 1 : 0)) / 2;
    if (pair_count > kMaximumDirectPairs ||
        pair_count * (1 + 2 * dimension) > kMaximumDirectWork) {
      throw BudgetExceeded{};
    }
    const Values values{layout, current_side, current_vertex, candidate};
    const cpp_int classes = integer_power(radix, 2 * dimension);
    Work work{work_budget};
    cpp_int total = cpp_int(edge_count) * classes;
    for (std::size_t i = 0; i < edge_count; ++i) {
      for (std::size_t j = 0; j < i; ++j) {
        std::uint64_t charged = 0;
        total += pair_term(values, radix, dimension, classes, edge_rows[i],
                           edge_columns[i], edge_rows[j], edge_columns[j], charged);
        work.add(charged);
      }
    }
    const std::string result = total.convert_to<std::string>();
    if (work_output != nullptr) *work_output = work.used;
    if (score_output == nullptr || result.size() + 1 > score_output_capacity) {
      write_text(error_output, error_output_capacity, "score output buffer is too small");
      return VERITAS_D3_OUTPUT_TOO_SMALL;
    }
    write_text(score_output, score_output_capacity, result);
    return VERITAS_D3_OK;
  } catch (const BudgetExceeded&) {
    write_text(error_output, error_output_capacity, "edge-pair work budget exceeded");
    return VERITAS_D3_BUDGET_EXCEEDED;
  } catch (const CounterOverflow&) {
    write_text(error_output, error_output_capacity, "work counter overflow");
    return VERITAS_D3_COUNTER_OVERFLOW;
  } catch (const std::exception& error) {
    write_text(error_output, error_output_capacity, error.what());
    return VERITAS_D3_INVALID_INPUT;
  } catch (...) {
    write_text(error_output, error_output_capacity, "unknown C++ scorer failure");
    return VERITAS_D3_INVALID_INPUT;
  }
}

extern "C" int veritas_d3_vertex_scores(
    std::uint64_t radix, std::uint64_t dimension, std::size_t edge_count,
    const std::int64_t* edge_rows, const std::int64_t* edge_columns,
    std::size_t row_vertex_count, const std::int64_t* row_vertex_ids,
    const std::int16_t* row_assignments, std::size_t column_vertex_count,
    const std::int64_t* column_vertex_ids, const std::int16_t* column_assignments,
    std::uint32_t current_side, std::int64_t current_vertex,
    std::uint64_t candidate_count, char* score_output, std::size_t score_stride,
    char* parent_output, std::size_t parent_output_capacity, std::uint64_t work_budget,
    std::uint64_t* work_output, char* error_output, std::size_t error_output_capacity) {
  if (work_output != nullptr) *work_output = 0;
  if (parent_output != nullptr && parent_output_capacity > 0) parent_output[0] = '\0';
  if (error_output != nullptr && error_output_capacity > 0) error_output[0] = '\0';
  try {
    Request request{radix, dimension, edge_count, edge_rows, edge_columns,
                    row_vertex_count, row_vertex_ids, row_assignments,
                    column_vertex_count, column_vertex_ids, column_assignments,
                    current_side, current_vertex};
    const Layout layout = validate(request, nullptr, false);
    const cpp_int classes = integer_power(radix, 2 * dimension);
    if (candidate_count != integer_power(radix, dimension)) {
      throw std::invalid_argument("candidate_count does not equal radix**dimension");
    }
    if (candidate_count > 0 && (score_output == nullptr || score_stride == 0)) {
      throw std::invalid_argument("missing score output buffer");
    }
    if (candidate_count > kMaximumBatchCandidates ||
        candidate_count > std::numeric_limits<std::size_t>::max() / score_stride ||
        candidate_count * score_stride > kMaximumBatchOutputBytes) {
      throw BudgetExceeded{};
    }
    const std::uint64_t pair_count =
        static_cast<std::uint64_t>(edge_count) * (edge_count - (edge_count > 0 ? 1 : 0)) / 2;
    if (pair_count > kMaximumBatchPairs) throw BudgetExceeded{};
    const std::uint64_t maximum_batch_work =
        pair_count + (candidate_count + 1) * pair_count * (1 + 2 * dimension) +
        candidate_count;
    if (maximum_batch_work > kMaximumBatchWork) throw BudgetExceeded{};
    Work work{work_budget};

    // Keep only an O(M) incidence mask and edge-index list. Retaining the
    // incident/independent unordered pair sets needs O(M^2) memory at the
    // configured pair cap. Pair order remains lexicographic (i, j), matching
    // the reference scorer and its exact work charges.
    std::vector<std::uint8_t> incident_edge(edge_count, 0);
    std::vector<std::size_t> incident_indices;
    incident_indices.reserve(edge_count);
    for (std::size_t edge = 0; edge < edge_count; ++edge) {
      const bool incident =
          (current_side == 0 && edge_rows[edge] == current_vertex) ||
          (current_side == 1 && edge_columns[edge] == current_vertex);
      if (incident) {
        incident_edge[edge] = 1;
        incident_indices.push_back(edge);
      }
    }

    // Charge the same one classification unit per unordered pair as before.
    for (std::size_t i = 0; i < edge_count; ++i) {
      for (std::size_t j = 0; j < i; ++j) {
        work.add(1);  // classify whether this pair depends on the current vertex
      }
    }

    const Values plain{layout, 2, -1, nullptr};
    cpp_int base = cpp_int(edge_count) * classes;
    for (std::size_t i = 0; i < edge_count; ++i) {
      for (std::size_t j = 0; j < i; ++j) {
        if (incident_edge[i] || incident_edge[j]) continue;
        std::uint64_t charged = 0;
        base += pair_term(plain, radix, dimension, classes, edge_rows[i], edge_columns[i],
                          edge_rows[j], edge_columns[j], charged);
        work.add(charged);
      }
    }

    // Visit each pair touching the current vertex exactly once in the same
    // (i, j) order as the retained-vector implementation. If i is incident,
    // all j<i are included. Otherwise only the earlier incident indices are.
    auto for_each_incident_pair = [&](auto&& visit) {
      std::size_t incident_cursor = 0;
      for (std::size_t i = 0; i < edge_count; ++i) {
        if (incident_edge[i]) {
          while (incident_cursor < incident_indices.size() &&
                 incident_indices[incident_cursor] <= i) {
            ++incident_cursor;
          }
          for (std::size_t j = 0; j < i; ++j) visit(i, j);
        } else {
          for (std::size_t cursor = 0; cursor < incident_cursor; ++cursor) {
            visit(i, incident_indices[cursor]);
          }
        }
      }
    };

    // Parent score: the exact candidate average, i.e. `concreteD3ScoreParent`.
    cpp_int parent = base;
    for_each_incident_pair([&](std::size_t i, std::size_t j) {
      std::uint64_t charged = 0;
      parent += parent_pair_term(layout, current_side, current_vertex, radix, dimension,
                                 classes, edge_rows[i], edge_columns[i], edge_rows[j],
                                 edge_columns[j], charged);
      work.add(charged);
    });

    std::vector<std::uint32_t> candidate(dimension, 0);
    for (std::uint64_t index = 0; index < candidate_count; ++index) {
      std::uint64_t remainder = index;
      for (std::uint64_t slot = dimension; slot-- > 0;) {
        candidate[slot] = static_cast<std::uint32_t>(remainder % radix);
        remainder /= radix;
      }
      const Values values{layout, current_side, current_vertex, candidate.data()};
      cpp_int score = base;
      for_each_incident_pair([&](std::size_t i, std::size_t j) {
        std::uint64_t charged = 0;
        score += pair_term(values, radix, dimension, classes, edge_rows[i],
                           edge_columns[i], edge_rows[j], edge_columns[j], charged);
        work.add(charged);
      });
      work.add(1);  // candidate bookkeeping
      const std::string text = score.convert_to<std::string>();
      if (text.size() + 1 > score_stride) {
        write_text(error_output, error_output_capacity, "score stride is too small");
        return VERITAS_D3_OUTPUT_TOO_SMALL;
      }
      write_text(score_output + index * score_stride, score_stride, text);
    }

    const std::string parent_text = parent.convert_to<std::string>();
    if (parent_output == nullptr || parent_text.size() + 1 > parent_output_capacity) {
      write_text(error_output, error_output_capacity, "parent output buffer is too small");
      return VERITAS_D3_OUTPUT_TOO_SMALL;
    }
    write_text(parent_output, parent_output_capacity, parent_text);
    if (work_output != nullptr) *work_output = work.used;
    return VERITAS_D3_OK;
  } catch (const BudgetExceeded&) {
    write_text(error_output, error_output_capacity, "edge-pair work budget exceeded");
    return VERITAS_D3_BUDGET_EXCEEDED;
  } catch (const CounterOverflow&) {
    write_text(error_output, error_output_capacity, "work counter overflow");
    return VERITAS_D3_COUNTER_OVERFLOW;
  } catch (const std::exception& error) {
    write_text(error_output, error_output_capacity, error.what());
    return VERITAS_D3_INVALID_INPUT;
  } catch (...) {
    write_text(error_output, error_output_capacity, "unknown C++ scorer failure");
    return VERITAS_D3_INVALID_INPUT;
  }
}

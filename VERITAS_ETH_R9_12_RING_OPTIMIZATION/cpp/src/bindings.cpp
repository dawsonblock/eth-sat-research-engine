#include "veritas_d3_score.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace py = pybind11;

namespace {

constexpr std::uint64_t kUnlimited = std::numeric_limits<std::uint64_t>::max();
constexpr std::uint64_t kMaximumCandidates = 100000;
constexpr std::uint64_t kMaximumEdges = 100000;
constexpr std::uint64_t kMaximumPairs = 1000000;
constexpr std::uint64_t kMaximumBatchWork = 100000000;
constexpr std::size_t kMaximumVerticesPerSide = 10000;
constexpr std::size_t kScoreStride = 256;

template <typename T>
std::vector<T> bounded_integer_sequence(py::handle object, std::size_t maximum,
                                        const char* name) {
  if (!PySequence_Check(object.ptr()) || PyUnicode_Check(object.ptr()) ||
      PyBytes_Check(object.ptr())) {
    throw py::value_error(std::string(name) + " must be an integer sequence");
  }
  const auto length = PySequence_Size(object.ptr());
  if (length < 0) throw py::error_already_set();
  if (static_cast<std::size_t>(length) > maximum) {
    throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: " + std::string(name) +
                          " length exceeds resource cap");
  }
  std::vector<T> values;
  values.reserve(static_cast<std::size_t>(length));
  for (py::handle item : py::reinterpret_borrow<py::sequence>(object)) {
    if (!PyLong_Check(item.ptr()) || PyBool_Check(item.ptr())) {
      throw py::value_error(std::string(name) + " entries must be exact integers");
    }
    values.push_back(py::cast<T>(item));
  }
  return values;
}

std::uint64_t exact_unsigned(py::handle object, const char* name) {
  if (!PyLong_Check(object.ptr()) || PyBool_Check(object.ptr())) {
    throw py::value_error(std::string(name) + " must be an exact integer");
  }
  return py::cast<std::uint64_t>(object);
}

std::int64_t exact_signed(py::handle object, const char* name) {
  if (!PyLong_Check(object.ptr()) || PyBool_Check(object.ptr())) {
    throw py::value_error(std::string(name) + " must be an exact integer");
  }
  return py::cast<std::int64_t>(object);
}

[[noreturn]] void raise_status(int status, const std::string& message) {
  switch (status) {
    case VERITAS_D3_BUDGET_EXCEEDED:
      throw py::value_error(
          "VERITAS_D3_BUDGET_EXCEEDED: " + (message.empty() ? "work budget exceeded" : message));
    case VERITAS_D3_COUNTER_OVERFLOW:
      throw std::overflow_error(message.empty() ? "work counter overflow" : message);
    case VERITAS_D3_OUTPUT_TOO_SMALL:
      throw py::buffer_error(message.empty() ? "output buffer too small" : message);
    default:
      throw py::value_error(message.empty() ? "invalid scorer input" : message);
  }
}

/// The C ABI indexes `assignments[index * dimension + coordinate]`, so a
/// short vector would be read past its end.  The vector sizes are available
/// here even though the ABI only sees pointers, so enforce the shape.
void require_assignment_shape(const std::vector<std::int64_t>& ids,
                              const std::vector<std::int16_t>& assignments,
                              std::uint64_t dimension, const char* name) {
  if (assignments.size() != ids.size() * static_cast<std::size_t>(dimension)) {
    throw py::value_error(std::string(name) +
                          " length must equal the vertex count times dimension");
  }
}

/// Mirror of `streaming._candidate_score` for one candidate label.
std::pair<std::string, std::uint64_t> candidate_score(
    std::uint64_t radix, std::uint64_t dimension,
    const std::vector<std::int64_t>& edge_rows,
    const std::vector<std::int64_t>& edge_columns,
    const std::vector<std::int64_t>& row_ids,
    const std::vector<std::int16_t>& row_assignments,
    const std::vector<std::int64_t>& column_ids,
    const std::vector<std::int16_t>& column_assignments, std::uint32_t current_side,
    std::int64_t current_vertex, const std::vector<std::uint32_t>& candidate,
    std::uint64_t work_budget) {
  if (edge_rows.size() != edge_columns.size()) {
    throw py::value_error("edge row and column arrays differ in length");
  }
  if (edge_rows.size() > kMaximumEdges) {
    throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: C++ edge cap exceeded");
  }
  if (radix < 2 || radix > 64 || dimension == 0 || dimension > 64 ||
      candidate.size() != dimension) {
    throw py::value_error("invalid scorer dimensions or candidate shape");
  }
  require_assignment_shape(row_ids, row_assignments, dimension, "row_assignments");
  require_assignment_shape(column_ids, column_assignments, dimension,
                           "column_assignments");
  const std::uint64_t edge_count = edge_rows.size();
  const std::uint64_t pair_count = edge_count * (edge_count - (edge_count > 0 ? 1 : 0)) / 2;
  if (pair_count > kMaximumPairs ||
      pair_count * (1 + 2 * dimension) > kMaximumBatchWork) {
    throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: direct hard work cap exceeded");
  }
  std::vector<char> score(kScoreStride);
  std::vector<char> error(512);
  std::uint64_t work = 0;
  const auto budget = work_budget;
  const int status = veritas_d3_candidate_score(
      radix, dimension, edge_rows.size(), edge_rows.data(), edge_columns.data(),
      row_ids.size(), row_ids.data(), row_assignments.data(), column_ids.size(),
      column_ids.data(), column_assignments.data(), current_side, current_vertex,
      candidate.data(), budget, score.data(), score.size(), &work, error.data(),
      error.size());
  if (status != VERITAS_D3_OK) raise_status(status, std::string(error.data()));
  return {std::string(score.data()), work};
}

py::tuple candidate_score_api(
    py::object radix_object, py::object dimension_object,
    py::handle edge_rows_object, py::handle edge_columns_object,
    py::handle row_ids_object, py::handle row_assignments_object,
    py::handle column_ids_object, py::handle column_assignments_object,
    py::object current_side_object, py::object current_vertex_object,
    py::handle candidate_object, py::object budget_object) {
  const auto radix = exact_unsigned(radix_object, "radix");
  const auto dimension = exact_unsigned(dimension_object, "dimension");
  const auto side = exact_unsigned(current_side_object, "current_side");
  if (side > std::numeric_limits<std::uint32_t>::max()) {
    throw py::value_error("current_side is outside uint32 range");
  }
  const auto vertex = exact_signed(current_vertex_object, "current_vertex");
  const auto budget = exact_unsigned(budget_object, "work_budget");
  auto edge_rows = bounded_integer_sequence<std::int64_t>(edge_rows_object,
                                                           kMaximumEdges, "edge_rows");
  auto edge_columns = bounded_integer_sequence<std::int64_t>(edge_columns_object,
                                                              kMaximumEdges, "edge_columns");
  auto row_ids = bounded_integer_sequence<std::int64_t>(row_ids_object,
                                                        kMaximumVerticesPerSide, "row_ids");
  auto row_assignments = bounded_integer_sequence<std::int16_t>(
      row_assignments_object, kMaximumVerticesPerSide * 64, "row_assignments");
  auto column_ids = bounded_integer_sequence<std::int64_t>(
      column_ids_object, kMaximumVerticesPerSide, "column_ids");
  auto column_assignments = bounded_integer_sequence<std::int16_t>(
      column_assignments_object, kMaximumVerticesPerSide * 64, "column_assignments");
  auto candidate = bounded_integer_sequence<std::uint32_t>(candidate_object, 64,
                                                            "candidate");
  const auto result = candidate_score(radix, dimension, edge_rows, edge_columns,
      row_ids, row_assignments, column_ids, column_assignments,
      static_cast<std::uint32_t>(side), vertex, candidate, budget);
  return py::make_tuple(py::str(result.first), result.second);
}

/// Evaluate every candidate label for one vertex step.
py::tuple vertex_scores(std::uint64_t radix, std::uint64_t dimension,
                        const std::vector<std::int64_t>& edge_rows,
                        const std::vector<std::int64_t>& edge_columns,
                        const std::vector<std::int64_t>& row_ids,
                        const std::vector<std::int16_t>& row_assignments,
                        const std::vector<std::int64_t>& column_ids,
                        const std::vector<std::int16_t>& column_assignments,
                        std::uint32_t current_side, std::int64_t current_vertex,
                        std::uint64_t work_budget) {
  if (edge_rows.size() != edge_columns.size()) {
    throw py::value_error("edge row and column arrays differ in length");
  }
  if (edge_rows.size() > kMaximumEdges) {
    throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: C++ edge cap exceeded");
  }
  if (radix < 2 || radix > 64 || dimension == 0 || dimension > 64) {
    throw py::value_error("invalid scorer dimensions");
  }
  require_assignment_shape(row_ids, row_assignments, dimension, "row_assignments");
  require_assignment_shape(column_ids, column_assignments, dimension,
                           "column_assignments");
  std::uint64_t count = 1;
  for (std::uint64_t i = 0; i < dimension; ++i) {
    if (count > kMaximumCandidates / radix) {
      throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: batch candidate cap exceeded");
    }
    count *= radix;
  }
  if (count > kMaximumCandidates) {
    throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: batch candidate cap exceeded");
  }
  const std::uint64_t edge_count = edge_rows.size();
  const std::uint64_t pair_count = edge_count * (edge_count - (edge_count > 0 ? 1 : 0)) / 2;
  if (pair_count > kMaximumPairs ||
      pair_count + (count + 1) * pair_count * (1 + 2 * dimension) + count >
          kMaximumBatchWork) {
    throw py::value_error("VERITAS_D3_BUDGET_EXCEEDED: batch hard work cap exceeded");
  }
  const std::size_t stride = kScoreStride;
  std::vector<char> scores(count * stride, '\0');
  std::vector<char> parent(stride, '\0');
  std::vector<char> error(512);
  std::uint64_t work = 0;
  const auto budget = work_budget;
  const int status = veritas_d3_vertex_scores(
      radix, dimension, edge_rows.size(), edge_rows.data(), edge_columns.data(),
      row_ids.size(), row_ids.data(), row_assignments.data(), column_ids.size(),
      column_ids.data(), column_assignments.data(), current_side, current_vertex, count,
      scores.data(), stride, parent.data(), parent.size(), budget, &work, error.data(),
      error.size());
  if (status != VERITAS_D3_OK) raise_status(status, std::string(error.data()));
  py::list result;
  for (std::uint64_t i = 0; i < count; ++i) {
    result.append(py::str(scores.data() + i * stride));
  }
  return py::make_tuple(result, py::str(parent.data()), work);
}

py::tuple vertex_scores_api(
    py::object radix_object, py::object dimension_object,
    py::handle edge_rows_object, py::handle edge_columns_object,
    py::handle row_ids_object, py::handle row_assignments_object,
    py::handle column_ids_object, py::handle column_assignments_object,
    py::object current_side_object, py::object current_vertex_object,
    py::object budget_object) {
  const auto radix = exact_unsigned(radix_object, "radix");
  const auto dimension = exact_unsigned(dimension_object, "dimension");
  const auto side = exact_unsigned(current_side_object, "current_side");
  if (side > std::numeric_limits<std::uint32_t>::max()) {
    throw py::value_error("current_side is outside uint32 range");
  }
  const auto vertex = exact_signed(current_vertex_object, "current_vertex");
  const auto budget = exact_unsigned(budget_object, "work_budget");
  auto edge_rows = bounded_integer_sequence<std::int64_t>(edge_rows_object,
                                                           kMaximumEdges, "edge_rows");
  auto edge_columns = bounded_integer_sequence<std::int64_t>(edge_columns_object,
                                                              kMaximumEdges, "edge_columns");
  auto row_ids = bounded_integer_sequence<std::int64_t>(row_ids_object,
                                                        kMaximumVerticesPerSide, "row_ids");
  auto row_assignments = bounded_integer_sequence<std::int16_t>(
      row_assignments_object, kMaximumVerticesPerSide * 64, "row_assignments");
  auto column_ids = bounded_integer_sequence<std::int64_t>(
      column_ids_object, kMaximumVerticesPerSide, "column_ids");
  auto column_assignments = bounded_integer_sequence<std::int16_t>(
      column_assignments_object, kMaximumVerticesPerSide * 64, "column_assignments");
  return vertex_scores(radix, dimension, edge_rows, edge_columns, row_ids,
      row_assignments, column_ids, column_assignments,
      static_cast<std::uint32_t>(side), vertex, budget);
}

}  // namespace

PYBIND11_MODULE(veritas_d3, module) {
  module.doc() =
      "Exact C++20 backend for the VERITAS-ETH R9.1 D.3 candidate scorer. "
      "Scores are returned as decimal strings so no precision is lost.";
  module.attr("ALGORITHM_VERSION") = veritas_d3_algorithm_version();
  module.def("candidate_score", &candidate_score_api, py::arg("radix"), py::arg("dimension"),
             py::arg("edge_rows"), py::arg("edge_columns"), py::arg("row_ids"),
             py::arg("row_assignments"), py::arg("column_ids"),
             py::arg("column_assignments"), py::arg("current_side"),
             py::arg("current_vertex"), py::arg("candidate"),
             py::arg("work_budget") = kUnlimited);
  module.def("vertex_scores", &vertex_scores_api, py::arg("radix"), py::arg("dimension"),
             py::arg("edge_rows"), py::arg("edge_columns"), py::arg("row_ids"),
             py::arg("row_assignments"), py::arg("column_ids"),
             py::arg("column_assignments"), py::arg("current_side"),
             py::arg("current_vertex"), py::arg("work_budget") = kUnlimited);
}

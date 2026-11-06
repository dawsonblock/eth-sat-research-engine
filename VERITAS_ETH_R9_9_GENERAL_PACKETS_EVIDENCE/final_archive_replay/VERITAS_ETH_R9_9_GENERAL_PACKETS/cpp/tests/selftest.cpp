// Dependency-free self-test for the C++ scorer.  It exercises the same
// three-edge fixture that `proofs/D3PythonOrder.lean` checks in the kernel,
// so a broken build fails before any Python test runs.

#include "veritas_d3_score.h"

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace {

int failures = 0;

void expect(bool condition, const char* message) {
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    ++failures;
  }
}

void expect_text(const std::string& actual, const std::string& expected,
                 const char* message) {
  if (actual != expected) {
    std::fprintf(stderr, "FAIL: %s (got %s, want %s)\n", message, actual.c_str(),
                 expected.c_str());
    ++failures;
  }
}

std::string score(const std::vector<std::int64_t>& rows,
                  const std::vector<std::int64_t>& columns,
                  const std::vector<std::int64_t>& row_ids,
                  const std::vector<std::int16_t>& row_values,
                  const std::vector<std::int64_t>& column_ids,
                  const std::vector<std::int16_t>& column_values,
                  std::uint32_t side, std::int64_t vertex,
                  const std::vector<std::uint32_t>& candidate) {
  std::vector<char> output(8192);
  std::vector<char> error(512);
  std::uint64_t work = 0;
  const int status = veritas_d3_candidate_score(
      2, 1, rows.size(), rows.data(), columns.data(), row_ids.size(), row_ids.data(),
      row_values.data(), column_ids.size(), column_ids.data(), column_values.data(), side,
      vertex, candidate.data(), UINT64_MAX, output.data(), output.size(), &work,
      error.data(), error.size());
  expect(status == VERITAS_D3_OK, error.data());
  return std::string(output.data());
}

}  // namespace

int main() {
  expect(std::strlen(veritas_d3_algorithm_version()) > 0, "algorithm version present");

  const std::vector<std::int64_t> rows{0, 1, 0};
  const std::vector<std::int64_t> columns{0, 1, 1};
  const std::vector<std::int64_t> row_ids{0, 1};
  const std::vector<std::int64_t> column_ids{0, 1};
  const std::vector<std::int16_t> empty{ -1, -1, -1, -1 };

  expect_text(score(rows, columns, row_ids, empty, column_ids, empty, 2, -1, {0}), "22",
              "initial scaled score matches the kernel fixture");

  const std::vector<std::int16_t> row_zero{0, -1, -1, -1};
  expect_text(score(rows, columns, row_ids, row_zero, column_ids, empty, 2, -1, {0}), "22",
              "second-step parent score matches the kernel fixture");
  expect_text(score(rows, columns, row_ids, row_zero, column_ids, empty, 0, 1, {1}), "16",
              "second-step candidate score matches the kernel fixture");

  // Batch path: all candidates for the first vertex, plus the parent score.
  {
    const std::size_t stride = 8192;
    std::vector<char> scores(2 * stride, '\0');
    std::vector<char> parent(stride, '\0');
    std::vector<char> error(512);
    std::uint64_t work = 0;
    const int status = veritas_d3_vertex_scores(
        2, 1, rows.size(), rows.data(), columns.data(), row_ids.size(), row_ids.data(),
        empty.data(), column_ids.size(), column_ids.data(), empty.data(), 0, 0, 2,
        scores.data(), stride, parent.data(), parent.size(), UINT64_MAX, &work,
        error.data(), error.size());
    expect(status == VERITAS_D3_OK, error.data());
    expect_text(std::string(parent.data()), "22", "batch parent score");
    expect_text(std::string(scores.data()), "22", "batch candidate [0]");
    expect_text(std::string(scores.data() + stride), "22", "batch candidate [1]");
    expect(work > 0, "batch path charges work");
  }

  // A 1,000-edge input has 499,500 unordered pairs. The batch path must
  // compute it with linear scratch state while agreeing with the independent
  // direct scorer on every candidate.
  {
    constexpr std::size_t edge_count = 1000;
    const std::size_t stride = 8192;
    std::vector<std::int64_t> many_rows(edge_count);
    std::vector<std::int64_t> many_columns(edge_count, 0);
    std::vector<std::int64_t> many_row_ids(edge_count);
    std::vector<std::int16_t> many_row_values(edge_count, -1);
    for (std::size_t i = 0; i < edge_count; ++i) {
      many_rows[i] = static_cast<std::int64_t>(i);
      many_row_ids[i] = static_cast<std::int64_t>(i);
    }
    const std::vector<std::int64_t> one_column_id{0};
    const std::vector<std::int16_t> one_column_value{-1};
    std::vector<char> scores(2 * stride, '\0');
    std::vector<char> parent(stride, '\0');
    std::vector<char> error(512);
    std::uint64_t work = 0;
    const int status = veritas_d3_vertex_scores(
        2, 1, edge_count, many_rows.data(), many_columns.data(), edge_count,
        many_row_ids.data(), many_row_values.data(), one_column_id.size(),
        one_column_id.data(), one_column_value.data(), 0, 0, 2, scores.data(),
        stride, parent.data(), parent.size(), UINT64_MAX, &work, error.data(),
        error.size());
    expect(status == VERITAS_D3_OK, "large streamed batch completes under pair cap");
    expect(std::strlen(parent.data()) > 0, "large streamed batch returns parent score");
    expect_text(std::string(scores.data()),
                score(many_rows, many_columns, many_row_ids, many_row_values,
                      one_column_id, one_column_value, 0, 0, {0}),
                "large streamed batch candidate [0] matches direct scorer");
    expect_text(std::string(scores.data() + stride),
                score(many_rows, many_columns, many_row_ids, many_row_values,
                      one_column_id, one_column_value, 0, 0, {1}),
                "large streamed batch candidate [1] matches direct scorer");
    expect(work > 0, "large streamed batch reports bounded work");
  }

  if (failures == 0) std::printf("veritas_d3_selftest: PASS\n");
  return failures == 0 ? 0 : 1;
}

"""Optional exact C++20 implementation of the R9.1 D.3 candidate scorer.

Two native entry points are supported, in this order:

1. the optional pybind11 module ``veritas_d3`` built from ``cpp/src/bindings.cpp``;
2. the C ABI shared library built from ``cpp/src/score.cpp``, loaded with
   ``ctypes``.

The pure-Python scorer in :mod:`streaming` is always available and is the
reference implementation.  This module never compiles code, never substitutes
a backend silently, and never changes a score: every backend returns the exact
arbitrary-precision integer.  A native score that disagrees with the reference
is a hard error, not a fallback trigger.
"""
from __future__ import annotations

import ctypes
from functools import lru_cache
import os
from pathlib import Path
import sys

from .expectation import PackingBudgetExceeded, validate_edges


UINT64_MAX = (1 << 64) - 1
INT64_MAX = (1 << 63) - 1
MAX_CPP_EDGES = 100_000
MAX_CPP_VERTICES_PER_SIDE = 10_000
MAX_CPP_BATCH_CANDIDATES = 100_000
MAX_CPP_BATCH_PAIRS = 1_000_000
MAX_CPP_BATCH_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_CPP_BATCH_TOTAL_WORK = 100_000_000
MAX_CPP_DIRECT_PAIRS = 1_000_000
MAX_CPP_DIRECT_WORK = 100_000_000
CPP_ALGORITHM_VERSION = "d3-streaming-cpp-direct-v1"
CPP_BATCH_ALGORITHM_VERSION = "d3-cpp20-direct-v1+batch-v1"
PYTHON_ALGORITHM_VERSION = "d3-streaming-python-direct-v1"
CPP_BATCH_WORK_METRIC_VERSION = "d3-batch-pair-score-work-v1"
SUPPORTED_BACKENDS = ("python", "cpp", "auto")
NATIVE_BACKEND_NAMES = ("cpp-pybind", "cpp-ctypes")


class CppBackendUnavailable(RuntimeError):
    """The requested native scorer is not available as a built library."""


def _build_dir() -> Path:
    repo = Path(__file__).resolve().parents[4]
    return Path(os.environ.get("VERITAS_D3_CPP_BUILD_DIR", repo / "build" / "cpp"))


def _library_candidates():
    override = os.environ.get("VERITAS_D3_CPP_LIBRARY")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise CppBackendUnavailable(f"configured C++ library does not exist: {path}")
        return [path]
    build_dir = _build_dir()
    names = ("veritas_d3_score.dll", "libveritas_d3_score.dylib",
             "libveritas_d3_score.so")
    return [build_dir / name for name in names]


@lru_cache(maxsize=8)
def _load_library(path: str):
    try:
        library = ctypes.CDLL(path)
        version = library.veritas_d3_algorithm_version
        version.argtypes = []
        version.restype = ctypes.c_char_p
        found_version = version().decode("ascii")
        if found_version != CPP_BATCH_ALGORITHM_VERSION:
            raise CppBackendUnavailable(
                f"C++ scorer ABI version mismatch: {found_version}")
        function = library.veritas_d3_candidate_score
        batch = library.veritas_d3_vertex_scores
    except (OSError, AttributeError, UnicodeError) as exc:
        raise CppBackendUnavailable(f"could not load C++ scoring library {path}: {exc}") from exc
    function.argtypes = [
        ctypes.c_uint64, ctypes.c_uint64, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64),
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int16),
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int16),
        ctypes.c_uint32, ctypes.c_int64, ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_uint64, ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
    ]
    function.restype = ctypes.c_int
    batch.argtypes = [
        ctypes.c_uint64, ctypes.c_uint64, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64),
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int16),
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int16),
        ctypes.c_uint32, ctypes.c_int64, ctypes.c_uint64,
        ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
        ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
    ]
    batch.restype = ctypes.c_int
    return library, function, batch


def _find_library():
    for path in _library_candidates():
        if path.is_file():
            return path
    raise CppBackendUnavailable(
        "C++ scorer is not built; see docs/R91_CPP_BACKEND.md and build cpp/"
    )


@lru_cache(maxsize=4)
def _load_pybind_module():
    try:
        import veritas_d3  # type: ignore[import-not-found]
        if (getattr(veritas_d3, "ALGORITHM_VERSION", None) == CPP_BATCH_ALGORITHM_VERSION and
                callable(getattr(veritas_d3, "candidate_score", None)) and
                callable(getattr(veritas_d3, "vertex_scores", None))):
            return veritas_d3
    except Exception:
        pass
    build_dir = _build_dir() / "python"
    if build_dir.is_dir():
        entry = str(build_dir)
        if entry not in sys.path:
            sys.path.insert(0, entry)
        try:
            import veritas_d3  # type: ignore[import-not-found]
            if (getattr(veritas_d3, "ALGORITHM_VERSION", None) == CPP_BATCH_ALGORITHM_VERSION and
                    callable(getattr(veritas_d3, "candidate_score", None)) and
                    callable(getattr(veritas_d3, "vertex_scores", None))):
                return veritas_d3
            raise CppBackendUnavailable("pybind11 module has an unsupported scorer ABI")
        except Exception as exc:  # pragma: no cover - depends on the build
            raise CppBackendUnavailable(f"pybind11 module could not be imported: {exc}") from exc
    raise CppBackendUnavailable("pybind11 module veritas_d3 is not built")


def resolve_score_backend(requested: str):
    """Resolve ``python``/``cpp``/``auto``.

    Returns ``(name, handle)`` where ``handle`` is ``None`` for the pure-Python
    scorer, a ``(library, function, batch)`` triple for ctypes, or the
    pybind11 module object.
    """
    if requested not in SUPPORTED_BACKENDS:
        raise ValueError("score_backend must be one of: python, cpp, auto")
    if requested == "python":
        return "python", None
    try:
        module = _load_pybind_module()
        return "cpp-pybind", module
    except CppBackendUnavailable:
        pass
    try:
        path = _find_library()
        library, function, batch = _load_library(str(path.resolve()))
        function._veritas_library = library
        batch._veritas_library = library
        return "cpp-ctypes", (library, function, batch)
    except CppBackendUnavailable:
        if requested == "cpp":
            raise
        return "python", None


def _array(ctype, values):
    values = list(values)
    return (ctype * max(1, len(values)))(*(values if values else [0]))


def _validated_edges(edges):
    if not isinstance(edges, (list, tuple)):
        raise ValueError("edges must be a list or tuple")
    if len(edges) > MAX_CPP_EDGES:
        raise PackingBudgetExceeded("C++ scorer edge cap exceeded")
    return validate_edges(edges)


def _layout(edges, partial, *, r, a, vertex, label):
    """Validate inputs and build the flat assignment tables shared by both ABIs."""
    if type(r) is not int or not 2 <= r <= 64 or type(a) is not int or not 1 <= a <= 64:
        raise ValueError("invalid C++ scorer dimensions")
    edges = _validated_edges(edges)
    rows = sorted({edge[0] for edge in edges})
    columns = sorted({edge[1] for edge in edges})
    if len(rows) > MAX_CPP_VERTICES_PER_SIDE or len(columns) > MAX_CPP_VERTICES_PER_SIDE:
        raise PackingBudgetExceeded("C++ scorer per-side vertex cap exceeded")
    if any(vertex_id > INT64_MAX for vertex_id in (*rows, *columns)):
        raise ValueError("C++ scorer vertex IDs must fit a nonnegative int64")
    row_index = {vertex_id: i for i, vertex_id in enumerate(rows)}
    column_index = {vertex_id: i for i, vertex_id in enumerate(columns)}
    row_values = [-1] * (len(rows) * a)
    column_values = [-1] * (len(columns) * a)
    if not isinstance(partial, dict):
        raise ValueError("partial assignment must be a dictionary")
    if len(partial) > 2 * MAX_CPP_VERTICES_PER_SIDE * a:
        raise PackingBudgetExceeded("C++ scorer partial-assignment cap exceeded")
    for key, symbol in partial.items():
        if (not isinstance(key, tuple) or len(key) != 3 or
                key[0] not in ("R", "C") or type(key[1]) is not int or
                type(key[2]) is not int or not 0 <= key[2] < a or
                type(symbol) is not int or not 0 <= symbol < r):
            raise ValueError("invalid partial assignment for C++ scorer")
        side, vertex_id, coordinate = key
        indices = row_index if side == "R" else column_index
        if vertex_id not in indices:
            raise ValueError("partial assignment refers to a vertex absent from input edges")
        values = row_values if side == "R" else column_values
        index = indices[vertex_id] * a + coordinate
        if values[index] != -1:
            raise ValueError("duplicate partial assignment")
        values[index] = symbol

    if (not isinstance(vertex, tuple) or len(vertex) != 2 or
            vertex[0] not in ("R", "C", "") or type(vertex[1]) is not int):
        raise ValueError("invalid current vertex")
    if vertex[0] == "":
        current_side, current_id = 2, -1
    else:
        current_side = 0 if vertex[0] == "R" else 1
        current_id = vertex[1]
        if current_id < 0 or current_id > INT64_MAX:
            raise ValueError("current vertex ID must fit a nonnegative int64")
        table = row_index if current_side == 0 else column_index
        if current_id not in table:
            raise ValueError("current vertex is absent from input edges")
    if label is not None and not isinstance(label, (tuple, list)):
        raise ValueError("candidate label must be a tuple or list")
    if label is None:
        labels = [0] * a
    elif vertex[0] == "" and len(label) == 0:
        labels = [0] * a
    else:
        if len(label) != a or any(type(x) is not int or not 0 <= x < r for x in label):
            raise ValueError("candidate label has invalid shape or symbol")
        labels = list(label)
    return (rows, columns, row_values, column_values, current_side, current_id, labels)


def candidate_score_cpp(edges, partial, *, r: int, a: int, D: int,
                        vertex, label, max_work=None, function=None):
    """Evaluate the production score formula in C++ with an exact big integer.

    ``max_work`` is the remaining shared Python work budget.  A budget failure
    returns no score and is mapped to the same exception as the Python path.
    """
    if function is None:
        path = _find_library()
        library, function, batch = _load_library(str(path.resolve()))
        function._veritas_library = library
        batch._veritas_library = library
    if (type(r) is not int or not 2 <= r <= 64 or type(a) is not int or
            not 1 <= a <= 64):
        raise ValueError("invalid C++ scorer dimensions")
    if type(D) is not int or D != r ** (2 * a):
        raise ValueError("C++ scorer class count does not match radix and dimension")
    if max_work is not None and (type(max_work) is not int or max_work < 0):
        raise ValueError("C++ scorer work budget must be a nonnegative integer or None")
    edges = _validated_edges(edges)
    pair_count = len(edges) * (len(edges) - 1) // 2
    direct_work_bound = pair_count * (1 + 2 * a)
    if pair_count > MAX_CPP_DIRECT_PAIRS or direct_work_bound > MAX_CPP_DIRECT_WORK:
        raise PackingBudgetExceeded("C++ direct scorer hard work cap exceeded")
    rows, columns, row_values, column_values, current_side, current_id, labels = _layout(
        edges, partial, r=r, a=a, vertex=vertex, label=label)
    row_edges = _array(ctypes.c_int64, (edge[0] for edge in edges))
    column_edges = _array(ctypes.c_int64, (edge[1] for edge in edges))
    row_ids = _array(ctypes.c_int64, rows)
    col_ids = _array(ctypes.c_int64, columns)
    row_assignment_array = _array(ctypes.c_int16, row_values)
    col_assignment_array = _array(ctypes.c_int16, column_values)
    candidate_array = _array(ctypes.c_uint32, labels)
    budget = UINT64_MAX if max_work is None else min(max_work, UINT64_MAX)
    score_output = ctypes.create_string_buffer(4096)
    error_output = ctypes.create_string_buffer(512)
    work_output = ctypes.c_uint64(0)
    status = function(
        r, a, len(edges), row_edges, column_edges,
        len(rows), row_ids, row_assignment_array,
        len(columns), col_ids, col_assignment_array,
        current_side, current_id, candidate_array, budget,
        score_output, len(score_output), ctypes.byref(work_output),
        error_output, len(error_output),
    )
    message = error_output.value.decode("utf-8", errors="replace")
    if status == 0:
        return int(score_output.value), work_output.value
    if status == 2:
        raise PackingBudgetExceeded(message or "C++ scorer work budget exceeded")
    if status == 3:
        raise OverflowError(message or "C++ scorer work counter overflow")
    if status == 4:
        raise BufferError(message or "C++ scorer output too small")
    raise ValueError(message or f"C++ scorer rejected input with status {status}")


def _flat_inputs(edges, partial, r, a, vertex):
    edges = _validated_edges(edges)
    rows, columns, row_values, column_values, current_side, current_id, _ = _layout(
        edges, partial, r=r, a=a, vertex=vertex, label=None)
    return (rows, columns, row_values, column_values, current_side, current_id)


def vertex_scores_ctypes(edges, partial, *, r: int, a: int, vertex,
                         max_work=None, handle=None):
    """All ``r**a`` candidate scores plus the parent score, via the C ABI."""
    if handle is None:
        path = _find_library()
        library, function, batch = _load_library(str(path.resolve()))
        function._veritas_library = library
        batch._veritas_library = library
    else:
        _, _, batch = handle
    if max_work is not None and (type(max_work) is not int or max_work < 0):
        raise ValueError("C++ scorer work budget must be a nonnegative integer or None")
    edges = _validated_edges(edges)
    rows, columns, row_values, column_values, current_side, current_id = _flat_inputs(
        edges, partial, r, a, vertex)
    count = r ** a
    _check_batch_limits(edges, count, a)
    stride = 256
    row_edges = _array(ctypes.c_int64, (edge[0] for edge in edges))
    column_edges = _array(ctypes.c_int64, (edge[1] for edge in edges))
    row_ids = _array(ctypes.c_int64, rows)
    col_ids = _array(ctypes.c_int64, columns)
    row_assignment_array = _array(ctypes.c_int16, row_values)
    col_assignment_array = _array(ctypes.c_int16, column_values)
    scores = ctypes.create_string_buffer(count * stride)
    parent = ctypes.create_string_buffer(stride)
    error_output = ctypes.create_string_buffer(512)
    work_output = ctypes.c_uint64(0)
    budget = UINT64_MAX if max_work is None else min(max_work, UINT64_MAX)
    status = batch(
        r, a, len(edges), row_edges, column_edges,
        len(rows), row_ids, row_assignment_array,
        len(columns), col_ids, col_assignment_array,
        current_side, current_id, count,
        scores, stride, parent, stride, budget,
        ctypes.byref(work_output), error_output, len(error_output),
    )
    message = error_output.value.decode("utf-8", errors="replace")
    if status != 0:
        if status == 2:
            raise PackingBudgetExceeded(message or "C++ scorer work budget exceeded")
        if status == 3:
            raise OverflowError(message or "C++ scorer work counter overflow")
        if status == 4:
            raise BufferError(message or "C++ scorer output too small")
        raise ValueError(message or f"C++ scorer rejected input with status {status}")
    raw = scores.raw
    decoded = [int(raw[i * stride: raw.index(b"\0", i * stride)]) for i in range(count)]
    return decoded, int(parent.value), work_output.value


def vertex_scores_pybind(edges, partial, *, r: int, a: int, vertex,
                         max_work=None, module=None):
    """All ``r**a`` candidate scores plus the parent score, via pybind11."""
    if module is None:
        module = _load_pybind_module()
    if max_work is not None and (type(max_work) is not int or max_work < 0):
        raise ValueError("C++ scorer work budget must be a nonnegative integer or None")
    edges = _validated_edges(edges)
    rows, columns, row_values, column_values, current_side, current_id = _flat_inputs(
        edges, partial, r, a, vertex)
    _check_batch_limits(edges, r ** a, a)
    try:
        scores, parent, work = module.vertex_scores(
            r, a, [edge[0] for edge in edges], [edge[1] for edge in edges],
            rows, row_values, columns, column_values,
            current_side, current_id,
            UINT64_MAX if max_work is None else min(max_work, UINT64_MAX))
    except ValueError as exc:
        if str(exc).startswith("VERITAS_D3_BUDGET_EXCEEDED:"):
            raise PackingBudgetExceeded(str(exc).split(":", 1)[1].strip()) from exc
        raise
    return [int(value) for value in scores], int(parent), work


def _check_batch_limits(edges, candidate_count, dimension):
    if candidate_count > MAX_CPP_BATCH_CANDIDATES:
        raise PackingBudgetExceeded("C++ batch candidate cap exceeded")
    pair_count = len(edges) * (len(edges) - 1) // 2
    if pair_count > MAX_CPP_BATCH_PAIRS:
        raise PackingBudgetExceeded("C++ batch pair-record cap exceeded")
    if candidate_count * 256 > MAX_CPP_BATCH_OUTPUT_BYTES:
        raise PackingBudgetExceeded("C++ batch output-byte cap exceeded")
    if type(dimension) is not int or not 1 <= dimension <= 64:
        raise ValueError("invalid C++ batch dimensions")
    pair_work_bound = (pair_count + (candidate_count + 1) * pair_count *
                       (1 + 2 * dimension) + candidate_count)
    if pair_work_bound > MAX_CPP_BATCH_TOTAL_WORK:
        raise PackingBudgetExceeded("C++ batch hard work cap exceeded")


def check_batch_limits(edges, *, radix: int, dimension: int,
                       total_work_bound: int | None = None):
    """Validate every native batch cap before the first C++ scorer call."""
    if (type(radix) is not int or not 2 <= radix <= 64 or
            type(dimension) is not int or not 1 <= dimension <= 64):
        raise ValueError("invalid C++ batch dimensions")
    edges = _validated_edges(edges)
    rows = {edge[0] for edge in edges}
    columns = {edge[1] for edge in edges}
    if len(rows) > MAX_CPP_VERTICES_PER_SIDE or len(columns) > MAX_CPP_VERTICES_PER_SIDE:
        raise PackingBudgetExceeded("C++ scorer per-side vertex cap exceeded")
    candidates = radix ** dimension
    _check_batch_limits(edges, candidates, dimension)
    if total_work_bound is not None and total_work_bound > MAX_CPP_BATCH_TOTAL_WORK:
        raise PackingBudgetExceeded("C++ streaming hard work cap exceeded")

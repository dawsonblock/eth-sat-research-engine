"""Differential and negative tests for the R9.1 C++20 scoring backend.

Every native result is compared against the pure-Python reference.  A native
backend that is not built is skipped, never silently replaced.
"""
from __future__ import annotations

import itertools
import random

import pytest

from veritas.research.eth_packing_v26 import cpp_backend
from veritas.research.eth_packing_v26.expectation import PackingBudgetExceeded
from veritas.research.eth_packing_v26.streaming import (
    _candidate_score,
    _ordered_vertices,
    construct_streaming_d3_packing,
)
from veritas.research.eth_packing_v26.streaming_check import (
    verify_streaming_d3_certificate,
)


def _available_backends():
    names = []
    for requested in ("cpp-pybind", "cpp-ctypes"):
        try:
            name, handle = cpp_backend.resolve_score_backend("cpp")
        except cpp_backend.CppBackendUnavailable:
            return []
        names.append((name, handle))
        break
    return names


BACKENDS = _available_backends()
requires_native = pytest.mark.skipif(not BACKENDS, reason="C++ scorer is not built")


class _Counter:
    def __init__(self, limit=None):
        self.limit = limit
        self.used = 0

    def tick(self, amount=1):
        self.used += amount
        if self.limit is not None and self.used > self.limit:
            raise PackingBudgetExceeded("budget")


def _python_score(edges, partial, r, a, vertex, label):
    return _candidate_score(edges, partial, r=r, a=a, D=r ** (2 * a),
                            vertex=vertex, label=label, work=_Counter())


def _native_scores(edges, partial, r, a, vertex):
    name, handle = BACKENDS[0]
    if name == "cpp-pybind":
        return cpp_backend.vertex_scores_pybind(edges, partial, r=r, a=a,
                                                vertex=vertex, module=handle)
    return cpp_backend.vertex_scores_ctypes(edges, partial, r=r, a=a,
                                            vertex=vertex, handle=handle)


def _random_case(rng):
    r = rng.choice([2, 3])
    a = rng.choice([1, 2])
    rows = rng.randint(1, 4)
    cols = rng.randint(1, 4)
    m = rng.randint(0, 7)
    edges = [(rng.randrange(rows), rng.randrange(cols)) for _ in range(m)]
    return edges, r, a


def _random_partial(rng, edges, r, a, upto):
    partial = {}
    order = _ordered_vertices(edges)
    for side, ident in order[:upto]:
        if rng.random() < 0.6:
            for d in range(a):
                partial[(side, ident, d)] = rng.randrange(r)
    return partial


@requires_native
def test_fixture_matches_python_reference():
    edges = [(0, 0), (1, 1), (0, 1)]
    for backend in ("python", "cpp", "auto"):
        built = construct_streaming_d3_packing(
            edges, r=2, a=1, max_work=None, max_candidate_evaluations=10 ** 6,
            score_backend=backend)
        cert = built.certificate
        assert cert["initial_expected_square_scaled"] == 22
        assert [step["expected_square_scaled"] for step in cert["steps"]] == [22, 16, 16, 12]
        assert [step["label"] for step in cert["steps"]] == [[0], [1], [0], [1]]
        assert cert["final_square_scaled"] == 12
        assert _ordered_vertices(edges) == (("R", 0), ("R", 1), ("C", 0), ("C", 1))


@requires_native
def test_backend_reports_native_algorithm():
    built = construct_streaming_d3_packing(
        [(0, 0), (1, 1)], r=2, a=1, max_work=None, max_candidate_evaluations=10 ** 6,
        score_backend="cpp")
    assert built.certificate["score_backend"] in cpp_backend.NATIVE_BACKEND_NAMES


@requires_native
def test_v4_native_certificate_has_independent_work_replay():
    built = construct_streaming_d3_packing(
        [(0, 0), (1, 1), (0, 1), (0, 1)], r=2, a=1,
        max_work=None, max_candidate_evaluations=10 ** 6,
        score_backend="cpp")
    certificate = built.certificate
    checked = verify_streaming_d3_certificate(certificate)
    assert certificate["schema"] == "VERITAS_ETH_D3_STREAMING_CERT_V4"
    assert checked["valid"] is True
    assert checked["independently_recomputed_construction_work_units"] == built.work_units
    assert checked["work_metric_version"] == cpp_backend.CPP_BATCH_WORK_METRIC_VERSION
    assert checked["paper_active_call_eligible"] is False

    changed = dict(certificate)
    changed["work_units"] += 1
    assert verify_streaming_d3_certificate(changed)["valid"] is False
    changed = dict(certificate)
    changed["policy"] = dict(certificate["policy"], work_metric_version="unknown")
    assert verify_streaming_d3_certificate(changed)["valid"] is False


@requires_native
def test_zero_work_budget_is_not_unlimited():
    name, handle = BACKENDS[0]
    with pytest.raises(PackingBudgetExceeded):
        if name == "cpp-pybind":
            cpp_backend.vertex_scores_pybind(
                [(0, 0)], {}, r=2, a=1, vertex=("R", 0), max_work=0,
                module=handle)
        else:
            cpp_backend.vertex_scores_ctypes(
                [(0, 0)], {}, r=2, a=1, vertex=("R", 0), max_work=0,
                handle=handle)


@requires_native
def test_batch_hard_caps_reject_before_scoring():
    # Pair-record and whole-call caps are applied before the initial C++ score.
    edges = [(0, 0)] * 1500
    with pytest.raises(PackingBudgetExceeded):
        construct_streaming_d3_packing(
            edges, r=2, a=1, max_work=None,
            max_candidate_evaluations=100, score_backend="cpp")


def test_pybind_sequence_and_boolean_caps_when_available():
    try:
        module = cpp_backend._load_pybind_module()
    except cpp_backend.CppBackendUnavailable:
        pytest.skip("optional pybind11 module is not built")
    with pytest.raises(ValueError, match="exact integer"):
        module.vertex_scores(True, 1, [], [], [], [], [], [], 2, -1,
                             cpp_backend.UINT64_MAX)
    oversized = [0] * 100_001
    with pytest.raises(ValueError, match="resource cap"):
        module.vertex_scores(2, 1, oversized, [], [], [], [], [], 2, -1,
                             cpp_backend.UINT64_MAX)


@requires_native
@pytest.mark.parametrize("seed", range(12))
def test_randomised_candidate_differential(seed):
    rng = random.Random(seed)
    for _ in range(8):
        edges, r, a = _random_case(rng)
        if not edges:
            continue
        order = _ordered_vertices(edges)
        for upto in range(len(order) + 1):
            partial = _random_partial(rng, edges, r, a, upto)
            for side, ident in order:
                expected = [_python_score(edges, partial, r, a, (side, ident), word)
                            for word in itertools.product(range(r), repeat=a)]
                scores, parent, _work = _native_scores(
                    edges, partial, r, a, (side, ident))
                assert scores == expected
                # The parent score is the average of the candidate scores.
                assert sum(expected) == parent * (r ** a)


@requires_native
def test_empty_and_singleton_graphs():
    for edges in ([], [(0, 0)]):
        for r, a in ((2, 1), (3, 2)):
            for backend in ("python", "cpp"):
                built = construct_streaming_d3_packing(
                    edges, r=r, a=a, max_work=None,
                    max_candidate_evaluations=10 ** 6, score_backend=backend)
                assert built.certificate["final_square_scaled"] == built.certificate[
                    "initial_expected_square_scaled"]


@requires_native
def test_edge_permutation_invariance():
    rng = random.Random(7)
    base = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 1)]
    reference = None
    for _ in range(10):
        edges = base[:]
        rng.shuffle(edges)
        built = construct_streaming_d3_packing(
            edges, r=2, a=1, max_work=None, max_candidate_evaluations=10 ** 6,
            score_backend="cpp")
        summary = (built.certificate["initial_expected_square_scaled"],
                   [step["expected_square_scaled"] for step in built.certificate["steps"]],
                   built.certificate["final_square_scaled"])
        if reference is None:
            reference = summary
        assert summary == reference


@requires_native
def test_duplicate_edges_are_counted_with_multiplicity():
    edges = [(0, 0), (0, 0), (0, 0)]
    built = construct_streaming_d3_packing(
        edges, r=2, a=1, max_work=None, max_candidate_evaluations=10 ** 6,
        score_backend="cpp")
    # Three identical edges always agree: M*D + 3 pairs * 2*D = 3*4 + 3*8 = 36.
    assert built.certificate["initial_expected_square_scaled"] == 36


@requires_native
def test_equal_numeric_ids_on_both_sides_stay_distinct():
    edges = [(0, 0)]
    assert _ordered_vertices(edges) == (("R", 0), ("C", 0))
    built = construct_streaming_d3_packing(
        edges, r=2, a=1, max_work=None, max_candidate_evaluations=10 ** 6,
        score_backend="cpp")
    assert built.certificate["row_labels"] == {"0": [0]}
    assert built.certificate["column_labels"] == {"0": [0]}


@requires_native
def test_tied_candidate_scores_choose_lexicographic_label():
    # A single edge with no constraints: every label ties, so label [0,0] wins.
    built = construct_streaming_d3_packing(
        [(0, 0)], r=3, a=2, max_work=None, max_candidate_evaluations=10 ** 6,
        score_backend="cpp")
    assert [step["label"] for step in built.certificate["steps"]] == [[0, 0], [0, 0]]


@requires_native
def test_large_integer_scores_are_exact():
    edges = [(0, 0), (1, 1), (2, 2), (0, 1)]
    for r, a in ((7, 4), (13, 3)):
        expected = _python_score(edges, {}, r, a, ("", -1), ())
        scores, parent, _work = _native_scores(edges, {}, r, a, ("", -1))
        assert expected == parent
        assert max(scores) >= expected


@requires_native
def test_budget_exhaustion_is_reported():
    edges = [(0, 0), (1, 1), (0, 1)]
    name, handle = BACKENDS[0]
    with pytest.raises(PackingBudgetExceeded):
        if name == "cpp-pybind":
            cpp_backend.vertex_scores_pybind(edges, {}, r=2, a=1, vertex=("R", 0),
                                             max_work=1, module=handle)
        else:
            cpp_backend.vertex_scores_ctypes(edges, {}, r=2, a=1, vertex=("R", 0),
                                             max_work=1, handle=handle)


@requires_native
def test_invalid_inputs_are_rejected():
    name, handle = BACKENDS[0]
    edges = [(0, 0), (1, 1)]
    cases = [
        dict(edges=edges, partial={("R", 5, 0): 0}),           # absent vertex
        dict(edges=edges, partial={("R", 0, 1): 0}),           # coordinate out of range
        dict(edges=edges, partial={("R", 0, 0): 9}),           # symbol out of radix
        dict(edges=edges, partial={"bad": 0}),                 # malformed key
    ]
    for case in cases:
        with pytest.raises(ValueError):
            if name == "cpp-pybind":
                cpp_backend.vertex_scores_pybind(case["edges"], case["partial"], r=2, a=1,
                                                 vertex=("R", 0), module=handle)
            else:
                cpp_backend.vertex_scores_ctypes(case["edges"], case["partial"], r=2, a=1,
                                                 vertex=("R", 0), handle=handle)
    with pytest.raises(ValueError):
        cpp_backend.resolve_score_backend("nonsense")


def test_python_backend_is_always_available():
    name, handle = cpp_backend.resolve_score_backend("python")
    assert name == "python" and handle is None


def test_auto_backend_never_raises_when_unbuilt(monkeypatch):
    monkeypatch.setenv("VERITAS_D3_CPP_BUILD_DIR", "/nonexistent")
    monkeypatch.delenv("VERITAS_D3_CPP_LIBRARY", raising=False)
    monkeypatch.setattr(cpp_backend, "_load_pybind_module",
                        lambda: (_ for _ in ()).throw(
                            cpp_backend.CppBackendUnavailable("not built")))
    name, handle = cpp_backend.resolve_score_backend("auto")
    assert name == "python" and handle is None
    with pytest.raises(cpp_backend.CppBackendUnavailable):
        cpp_backend.resolve_score_backend("cpp")


@requires_native
def test_binding_rejects_misshapen_assignment_tables():
    """The C ABI only sees pointers; the pybind11 layer must enforce shape.

    Regression: a short assignment vector was accepted and read past its end.
    """
    name, handle = BACKENDS[0]
    if name != "cpp-pybind":
        pytest.skip("shape validation lives in the pybind11 layer")
    with pytest.raises(ValueError):
        handle.candidate_score(2, 1, [0], [0], [0, 1], [0], [0], [-1], 2, -1, [0])
    with pytest.raises(ValueError):
        handle.candidate_score(2, 1, [0], [0], [0], [0], [0, 1], [0], 2, -1, [0])
    with pytest.raises(ValueError):
        handle.vertex_scores(2, 1, [0], [0], [0, 1], [0], [0], [-1], 2, -1)
    # A correctly shaped call still succeeds.
    score, _work = handle.candidate_score(
        2, 1, [0, 1, 0], [0, 1, 1], [0, 1], [-1, -1], [0, 1], [-1, -1], 2, -1, [0])
    assert int(score) == 22


def test_wide_vertex_ids_are_explicit_backend_boundary():
    """`auto` falls back for ids the int64 ABI cannot carry; `cpp` fails closed.

    The fallback event only exists when a native backend is selectable, so the
    reason is asserted only in that case.  The reference-equivalence assertion
    holds in every environment, including an unbuilt checkout.
    """
    edges = [(2 ** 63, 0)]
    built = construct_streaming_d3_packing(
        edges, r=2, a=1, max_work=None, max_candidate_evaluations=1000,
        score_backend="auto")
    certificate = built.certificate
    assert certificate["score_backend"] == "python"
    assert "score_backend_fallback_reason" not in certificate
    reference = construct_streaming_d3_packing(
        edges, r=2, a=1, max_work=None, max_candidate_evaluations=1000,
        score_backend="python")
    assert certificate["final_square_scaled"] == reference.certificate["final_square_scaled"]
    if BACKENDS:
        assert built.backend_fallback_reason == "vertex_id_exceeds_int64"
        with pytest.raises(ValueError):
            construct_streaming_d3_packing(
                edges, r=2, a=1, max_work=None, max_candidate_evaluations=1000,
                score_backend="cpp")

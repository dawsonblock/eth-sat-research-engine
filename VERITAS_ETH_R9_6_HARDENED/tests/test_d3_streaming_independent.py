from copy import deepcopy
import random

import pytest

from veritas.research.eth_packing_v26.streaming import (
    D3PreconditionsNotMet,
    construct_active_call_streaming_packing,
    construct_streaming_d3_packing,
)
from veritas.research.eth_packing_v26.streaming_check import (
    verify_streaming_d3_certificate,
)
from veritas.research.eth_packing_v26.expectation import PackingBudgetExceeded


@pytest.mark.parametrize("edges,r,a", [
    ([], 2, 1),
    ([(0, 0)], 2, 1),
    ([(0, 0), (0, 1), (1, 0)], 2, 1),
    ([(0, 0), (0, 0), (1, 1), (2, 2)], 2, 2),
    ([(0, 1), (0, 2), (1, 1), (2, 0)], 3, 1),
])
def test_streaming_labels_replay_by_independent_rational_oracle(edges, r, a):
    built = construct_streaming_d3_packing(
        edges, r=r, a=a, max_work=2_000_000,
        max_candidate_evaluations=100_000)
    checked = verify_streaming_d3_certificate(
        built.certificate, max_work=2_000_000,
        max_candidate_evaluations=100_000)
    assert checked["valid"]
    assert checked["independent_work_units"] == built.work_units
    assert checked["theorem_recursion_qualified"] is False
    assert built.certificate["resource_ledger"]["bit_complexity_complete"] is False


def test_certificate_detects_nonminimizer_wrong_score_and_label_substitution():
    built = construct_streaming_d3_packing(
        [(0, 0), (0, 1), (1, 0)], r=2, a=1,
        max_work=2_000_000, max_candidate_evaluations=100_000)
    original = built.certificate
    assert verify_streaming_d3_certificate(original)["valid"]

    altered = deepcopy(original)
    step = altered["steps"][0]
    step["label"] = [1 - step["label"][0]]
    assert not verify_streaming_d3_certificate(altered)["valid"]

    altered = deepcopy(original)
    altered["steps"][0]["expected_square_scaled"] += 1
    assert not verify_streaming_d3_certificate(altered)["valid"]

    altered = deepcopy(original)
    altered["steps"].reverse()
    assert not verify_streaming_d3_certificate(altered)["valid"]


def test_certificate_detects_changed_edges_padding_policy_and_load_claim():
    built = construct_streaming_d3_packing(
        [(0, 0), (0, 1), (1, 0), (1, 1)], r=2, a=1,
        max_work=2_000_000, max_candidate_evaluations=100_000)
    original = built.certificate
    assert verify_streaming_d3_certificate(original)["valid"]

    for mutate in (
        lambda c: c["edges"].__setitem__(0, [8, 9]),
        lambda c: c.__setitem__("H_pad", c["H_pad"] + 2),
        lambda c: c["policy"].__setitem__("max_candidate_evaluations", 0),
        lambda c: c["resource_ledger"].__setitem__("bit_complexity_complete", True),
        lambda c: c["steps"][0].__setitem__("expected_square_scaled", True),
        lambda c: c["preconditions"].__setitem__("M_ge_LD", 1),
    ):
        altered = deepcopy(original)
        mutate(altered)
        assert not verify_streaming_d3_certificate(altered)["valid"]


def test_active_paper_hypotheses_are_checked_before_labeling(monkeypatch):
    import veritas.research.eth_packing_v26.streaming as streaming

    def must_not_run(*args, **kwargs):
        raise AssertionError("labeler ran before active-call hypotheses")

    monkeypatch.setattr(streaming, "_candidate_score", must_not_run)
    with pytest.raises(D3PreconditionsNotMet, match="eq:tensor-packing-conditions"):
        construct_streaming_d3_packing(
            [(i, i) for i in range(8)], r=64, a=1,
            require_paper_conditions=True)

    result = construct_active_call_streaming_packing([(i, i) for i in range(8)], a=1)
    assert result["status"] == "INCONCLUSIVE_D3_PRECONDITIONS"
    assert result["packing"] is None and result["certificate"] is None


def test_rational_oracle_is_independent_of_production_labeler(monkeypatch):
    import veritas.research.eth_packing_v26.streaming as production

    built = production.construct_streaming_d3_packing(
        [(0, 0), (0, 1), (1, 0)], r=2, a=1,
        max_work=2_000_000, max_candidate_evaluations=100_000)
    monkeypatch.setattr(production, "_candidate_score",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    assert verify_streaming_d3_certificate(built.certificate)["valid"]


def test_checker_budgets_return_inconclusive_without_valid_result():
    built = construct_streaming_d3_packing(
        [(0, 0), (0, 1), (1, 0)], r=2, a=1,
        max_work=2_000_000, max_candidate_evaluations=100_000)
    result = verify_streaming_d3_certificate(
        built.certificate, max_work=0, max_candidate_evaluations=0)
    assert result["valid"] is False
    assert result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"

    with pytest.raises(ValueError, match="max_work"):
        construct_streaming_d3_packing([(0, 0)], r=2, a=1, max_work="unbounded")
    with pytest.raises(PackingBudgetExceeded, match="dimension"):
        construct_streaming_d3_packing([(0, 0)], r=2, a=65)
    result = construct_active_call_streaming_packing([(0, 0)], a=65)
    assert result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert result["packing"] is None


def test_toy_eligible_inequalities_replay_without_promoting_fixed_radix_claim():
    # A 4-regular bipartite graph satisfies the three inequalities for the
    # generic r=2,a=1 fixture. The manuscript fixes r=64, so this is a
    # mechanism check, not a paper-eligible theorem call.
    edges = [(i, (i + shift) % 32) for i in range(32) for shift in range(4)]
    built = construct_streaming_d3_packing(
        edges, r=2, a=1, max_work=4_000_000,
        max_candidate_evaluations=1_000)
    checked = verify_streaming_d3_certificate(
        built.certificate, max_work=4_000_000,
        max_candidate_evaluations=1_000)
    assert checked["valid"]
    assert checked["numeric_active_call_inequalities"] is True
    assert checked["packet_count_bound"] is True
    assert checked["port_load_bound"] is True
    assert checked["paper_active_call_eligible"] is False
    assert checked["universal_packing_lemma_proven"] is False


def test_sorted_python_order_differs_from_lean_order_audit_fixture():
    # The Lean fixture in D3SymbolPorts.lean is kernel-checked separately.
    # This Python check pins the other side of the concrete counterexample.
    built = construct_streaming_d3_packing([(0, 0), (1, 1), (0, 1)], r=2, a=1)
    assert dict(built.packing.rows) == {0: (0,), 1: (1,)}
    assert dict(built.packing.cols) == {0: (0,), 1: (1,)}
    assert [step["vertex"] for step in built.certificate["steps"]] == [0, 1, 0, 1]


def test_streaming_replay_never_infers_source_schedule_from_lemma_conditions():
    built = construct_streaming_d3_packing(
        [(0, 0)], r=64, a=1, max_work=100_000,
        max_candidate_evaluations=1000)
    assert built.certificate["paper_active_call_eligible"] is False
    checked = verify_streaming_d3_certificate(built.certificate)
    assert checked["valid"] and checked["source_schedule_checked"] is False
    assert checked["execution_backend"] == "python"
    assert checked["backend_independently_replayed"] is True
    forged = deepcopy(built.certificate)
    forged["paper_active_call_eligible"] = True
    assert not verify_streaming_d3_certificate(forged)["valid"]
    previous = deepcopy(built.certificate)
    previous["schema"] = "VERITAS_ETH_D3_STREAMING_CERT_V2"
    for field in ("algorithm_version", "score_backend_requested", "score_backend"):
        previous.pop(field)
    assert verify_streaming_d3_certificate(previous)["valid"]
    legacy = deepcopy(built.certificate)
    legacy["schema"] = "VERITAS_ETH_D3_STREAMING_CERT_V1"
    for field in ("algorithm_version", "score_backend_requested", "score_backend"):
        legacy.pop(field)
    checked = verify_streaming_d3_certificate(legacy)
    assert checked["valid"] and checked["legacy_active_call_claim_discarded"] is True
    assert checked["paper_active_call_eligible"] is False


@pytest.mark.parametrize("failed_bound", [
    "numeric_active_call_inequalities", "initial_variance_bound",
    "packet_count_bound", "port_load_bound",
])
def test_wrapper_rejects_a_valid_trace_when_a_required_bound_fails(monkeypatch, failed_bound):
    import veritas.research.eth_packing_v26.streaming as production
    import veritas.research.eth_packing_v26.streaming_check as checker
    from types import SimpleNamespace

    monkeypatch.setattr(production, "d3_preconditions", lambda *args: {
        "M_ge_2_D_squared_delta": True, "M_ge_LD": True, "2L_le_delta": True,
    })
    monkeypatch.setattr(production, "construct_streaming_d3_packing",
                        lambda *args, **kwargs: SimpleNamespace(packing=object(), certificate={}))
    replay = {"valid": True, "numeric_active_call_inequalities": True,
              "initial_variance_bound": True, "packet_count_bound": True,
              "port_load_bound": True}
    replay[failed_bound] = False
    monkeypatch.setattr(checker, "verify_streaming_d3_certificate", lambda *args, **kwargs: replay)
    result = production.construct_active_call_streaming_packing([(0, 0)], a=2)
    assert result["status"] == "INCONCLUSIVE_CERTIFICATE_REPLAY"
    assert result["packing"] is None and result["certificate"] is None


def test_seeded_small_multigraph_matrix_matches_independent_fraction_oracle():
    rng = random.Random(0xD3_2026)
    for case in range(12):
        left_count = 1 + case % 3
        right_count = 1 + (case // 2) % 3
        edge_count = case % 7
        edges = [(rng.randrange(left_count), rng.randrange(right_count))
                 for _ in range(edge_count)]
        radix = 2 + case % 2
        built = construct_streaming_d3_packing(
            edges, r=radix, a=1, max_work=500_000,
            max_candidate_evaluations=10_000)
        checked = verify_streaming_d3_certificate(
            built.certificate, max_work=500_000,
            max_candidate_evaluations=10_000)
        assert checked["valid"], (case, checked)


def test_partial_state_candidate_average_matches_fraction_oracle():
    """Check the Lean averaging contract against production and rational paths.

    The Lean theorem proves the abstract finite-term identity. This test
    checks concrete production scores against a separately coded Fraction
    probability calculation at arbitrary partially assigned states; it is a
    finite refinement check, not a formal proof of that refinement.
    """
    from itertools import product

    from veritas.research.eth_packing_v26.streaming import (
        _Work,
        _candidate_score,
        _ordered_vertices,
    )
    from veritas.research.eth_packing_v26.streaming_check import _reference_score

    rng = random.Random(0xA7E_2026)
    for case in range(24):
        left, right = 1 + case % 3, 1 + (case // 3) % 3
        edges = [(rng.randrange(left), rng.randrange(right))
                 for _ in range(case % 7)]
        if not edges:
            edges = [(0, 0)]
        radix, dimension = 2 + case % 2, 1 + (case // 2) % 2
        target = _ordered_vertices(edges)[case % len(_ordered_vertices(edges))]
        partial = {}
        for vertex in _ordered_vertices(edges):
            if vertex == target or rng.randrange(2) == 0:
                continue
            side, ident = vertex
            for coordinate in range(dimension):
                partial[(side, ident, coordinate)] = rng.randrange(radix)

        noop = lambda _amount=1: None
        D = radix ** (2 * dimension)
        parent = _reference_score(edges, partial, radix, dimension,
                                  ("", -1), (), noop)
        scores = []
        for label in product(range(radix), repeat=dimension):
            production = _candidate_score(
                edges, partial, r=radix, a=dimension, D=D,
                vertex=target, label=label, work=_Work(None))
            independent = _reference_score(
                edges, partial, radix, dimension, target, label, noop)
            assert production == independent
            scores.append(independent)
        assert sum(scores) == len(scores) * parent


from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
import shutil
from pathlib import Path
import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork, from_cnf, eliminate
from veritas.research.finite_reductions import (
    BoundaryPolicy,
    contract_boundary,
    replay_boundary,
)
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.paper_verification.exact_parameters import (
    check_schedule,
    source_schedule,
    hermite_parameters,
)
from veritas.research.paper_verification.boundary_identity import verify_boundary_tree
from veritas.research.paper_verification.child_identity import (
    construct_reduction,
    verify_reduction,
)
from veritas.research.paper_verification.hermite_checker import (
    check_functional,
    recover_reference,
)
from veritas.research.eth_interpolation.source_hermite import make_source_tapered_plan
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing,
    implicit_sparse_mode_source,
)


def test_registry_rejects_a_different_statement(tmp_path):
    paper = Path(__file__).resolve().parents[2] / "paper"
    assert len(source_registry()["labels"]) == 10
    shutil.copytree(paper, tmp_path / "p")
    file = tmp_path / "p/quantitative-contraction.tex"
    file.write_bytes(file.read_bytes().replace(b"3M/r", b"9M/r"))
    with pytest.raises(ValueError):
        source_registry(tmp_path / "p")


@pytest.mark.parametrize(
    "s", [2, 3, 4, 15, 16, 17, 31, 32, 33, 1023, 1024, 1025, 65536]
)
def test_integer_thresholds(s):
    q = source_schedule(s, 0)
    assert (q["degree_limit"] - 1) ** 10 < s**9 <= q["degree_limit"] ** 10
    for M in {q["leaf_threshold"] - 1, q["leaf_threshold"], q["leaf_threshold"] + 1, s}:
        report = check_schedule(s, M, int(M > 0), 0)
        assert report["parameters"] == q
        assert not report["active_identity_proved"]


def test_positive_active_numeric_example_only():
    s = 1 << 131080
    q = check_schedule(s, s, 1, 0)
    assert q["status"] == "ACTIVE_NUMERIC_PRECONDITIONS_MET"
    assert (
        q["parameters"]["u"],
        q["parameters"]["a"],
        q["parameters"]["packing_class_count"],
    ) == (1, 2, 1 << 24)
    assert check_schedule(s, s >> 3, 1, 1)["status"] == "INCONCLUSIVE_SCHEDULE"
    for bad in (0, 1, True):
        with pytest.raises(ValueError):
            source_schedule(bad, 0)
    with pytest.raises(ValueError):
        hermite_parameters(12, 2, 0, 15)


def test_hermite_guard_and_functional():
    plan = make_source_tapered_plan(M=4, a=2, u=1, p=3)
    assert check_functional(plan)["degree_bound"] == 28
    with pytest.raises(ValueError):
        check_functional(replace(plan, guard_bits=plan.guard_bits - 1))
    w = list(plan.weights)
    t, row = w[0]
    w[0] = (t, (row[0] + Fraction(1, 2), *row[1:]))
    with pytest.raises(ValueError):
        check_functional(replace(plan, weights=tuple(w)))
    # A constant integer at every node with zero higher Taylor coefficients.
    jets = {t: (5,) + (0,) * (len(row) - 1) for t, row in plan.weights}
    ps = {n.t: (n.precision_bits,) * len(jets[n.t]) for n in plan.nodes}
    assert recover_reference(plan, jets, ps) == 5
    t = plan.nodes[0].t
    ps[t] = tuple(x - 1 for x in ps[t])
    with pytest.raises(ValueError):
        recover_reference(plan, jets, ps)


@pytest.fixture(scope="module")
def point():
    net = from_cnf(CNF.from_lists(2, [[1, 2], [-1, 2]]))
    parent = describe_integer_network(
        net, creation_precision=3, defining_polynomial=first_irreducible(5)
    )
    src = implicit_sparse_mode_source(
        construct_implicit_packing(parent.bipartite_edges(), r=64, a=2)
    )
    params = hermite_parameters(4, 2, 1, 3)
    prec = next(n[-1] for n in params["nodes"] if n[0] == -1)
    m = make_point_modes(
        src,
        node=-1,
        precision=prec,
        extension_degree=5,
        zeta=(1, 0, 0, 0, 0),
        max_tuples=512,
    )
    args = dict(s=16, depth=0, u=1, p=3)
    return parent, m, construct_reduction(parent, m, **args), args


def test_64_group_source_formula_inactive(point):
    parent, m, c, kw = point
    report = verify_reduction(parent, m, c, **kw)
    assert (
        report["group_values_checked"] == 64 * report["tuples"] and report["tuples"] > 1
    )
    assert not c["source_active_execution"] and c["scheduled"]["parameters"]["u"] == 0
    assert not report["actual_packing"]["packet_bound_met"]


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "same-count",
        "group",
        "coefficient",
        "precision",
        "mode",
        "source",
        "equation",
        "parent",
        "scope",
        "recipe",
        "oracle",
    ],
)
def test_forged_certificate(point, attack):
    parent, m, c, kw = point
    bad = json.loads(json.dumps(c))
    terms = bad["child_sum"]["terms"]
    if attack == "missing":
        terms.pop()
    elif attack == "same-count":
        terms[-1] = terms[0]
    elif attack == "group":
        terms[0]["groups"].pop()
    elif attack == "coefficient":
        terms[0]["groups"][0][-1][0][0] += 1
    elif attack == "precision":
        bad["used"]["child_precision"] -= 1
    elif attack == "mode":
        bad["mode_certificate"]["modes"].pop()
    elif attack == "source":
        bad["paper_source_sha256"] = "a" * 64
    elif attack == "equation":
        bad["equation"] = "ordinary-cut"
    elif attack == "parent":
        bad["child_sum"]["parent_sha256"] = "a" * 64
    elif attack == "scope":
        bad["source_active_execution"] = True
    elif attack == "recipe":
        terms[-1]["groups"][0][2] = "b" * 64
    else:
        bad["independent_parent_value"][0] ^= 1
    assert "result" not in verify_reduction(parent, m, bad, **kw)


def test_two_dense_16_wire_factors():
    n = 16
    raw = (1,) * (1 << n)
    net = TensorNetwork(
        n,
        (
            Factor(tuple(range(n)), raw, "A"),
            Factor(tuple(reversed(range(n))), raw, "B"),
        ),
    )
    policy = BoundaryPolicy(on_call_overflow="certified_elimination")
    refused = contract_boundary(net, precision=17)
    assert (
        "result" not in refused
        and refused["ledger"]["counters"]["recursive_calls"] == 1
    )
    solved = contract_boundary(net, precision=17, policy=policy)
    c = solved["certificate"]
    assert c["tree"]["method"] == "certified_elimination" and solved["result"] == 65536
    assert verify_boundary_tree(net, c, precision=17, policy=policy)["result"] == 65536
    bad = deepcopy(c)
    bad["tree"]["steps"][0]["table_sha256"] = "0" * 64
    assert "result" not in verify_boundary_tree(net, bad, precision=17, policy=policy)


@pytest.mark.parametrize("n", [12, 14, 16])
def test_boundary_proof_and_shuffled_ports(n):
    net = TensorNetwork(
        n,
        tuple(Factor(((i + 1) % n, i), (1, -3, i, 1), "v") for i in reversed(range(n))),
    )
    policy = BoundaryPolicy(leaf_edges=3, verify_root=False)
    c = contract_boundary(net, precision=35, policy=policy)["certificate"]
    assert verify_boundary_tree(net, c, precision=35, policy=policy)[
        "result"
    ] == eliminate(net) % (1 << 35)
    c["tree"]["terms"].pop()
    assert "result" not in verify_boundary_tree(net, c, precision=35, policy=policy)


def test_json_reduction_is_portable_but_compensating_group_forgery_is_rejected(point):
    parent, m, c, kw = point
    saved = json.loads(json.dumps(c))
    assert (
        verify_reduction(parent, m, saved, **kw)["status"]
        == "VERIFIED_FINITE_POINT_IDENTITY"
    )
    term = saved["child_sum"]["terms"][0]
    free = [g for g in term["groups"] if g[1] == 0 and g[-1][0] == [1, 0, 0, 0, 0]]
    assert len(free) >= 2
    # Two minus signs keep the saved group product exactly unchanged.
    for group in free[:2]:
        group[-1][0][0] = (1 << m["precision"]) - 1
    assert "result" not in verify_reduction(parent, m, saved, **kw)

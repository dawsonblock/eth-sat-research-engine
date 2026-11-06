from copy import deepcopy
from dataclasses import replace
import json
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork, from_cnf, eliminate
from veritas.research.finite_reductions import boundary as engine
from veritas.research.finite_reductions import (
    BoundaryPolicy,
    contract_boundary,
    replay_boundary,
)
from veritas.research.finite_reductions import recipe_point as point
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing,
    implicit_sparse_mode_source,
)


def cycle(n, seed):
    rng = Random(seed)
    return TensorNetwork(
        n,
        tuple(
            Factor(
                (i, (i + 1) % n), tuple(rng.randint(-4, 5) for _ in range(4)), str(i)
            )
            for i in range(n)
        ),
    )


@pytest.mark.parametrize("n,p", [(12, 1), (12, 61), (14, 17), (16, 41)])
def test_signed_weighted_cycle(n, p):
    net = cycle(n, 91)
    policy = BoundaryPolicy(leaf_edges=3)
    out = contract_boundary(net, precision=p, policy=policy)
    assert out["result"] == eliminate(net) % (1 << p)
    assert out["ledger"]["maximum_depth"] >= 2
    assert out["direct_parent_checked"]
    assert out["certificate"]["tree"]["boundary"]
    reverse = TensorNetwork(
        n,
        tuple(
            Factor(tuple(n - 1 - i for i in f.ports), f.table, f.label)
            for f in reversed(net.factors)
        ),
    )
    assert (
        contract_boundary(reverse, precision=p, policy=policy)["result"]
        == out["result"]
    )


@pytest.mark.parametrize(
    "formula",
    [
        [[1, 2], [-1, 3], [-3, 2], [-2, 4], [4, -1], [-4, 1]],
        [[1], [-1], [2, 3], [-4, 1], [3, 4], [-3, 2], [4, -2]],
    ],
)
def test_cnf_exact_with_unused_variables(formula):
    cnf = CNF.from_lists(5, formula)
    expected = sum(
        cnf.evaluate({v: bool(i & (1 << (v - 1))) for v in range(1, 6)})
        for i in range(32)
    )
    net = from_cnf(cnf)
    assert net.edges == 12
    assert contract_boundary(net, precision=6)["result"] == expected


def test_high_degree_and_scalar():
    n = 10
    center = Factor(
        tuple(range(n)), tuple((i % 21) - 8 for i in range(1 << n)), "center"
    )
    net = TensorNetwork(
        n, (center,) + tuple(Factor((i,), (-1, 2), "leaf") for i in range(n))
    )
    assert contract_boundary(net, precision=40)["result"] == eliminate(net) % (1 << 40)
    assert (
        contract_boundary(
            TensorNetwork(0, (Factor((), (-3,), "constant"),)), precision=3
        )["result"]
        == 5
    )


@pytest.mark.parametrize(
    "change",
    ["mask", "missing", "group", "coefficient", "child", "result", "policy", "source"],
)
def test_regenerate_every_term(change):
    net = cycle(6, 2)
    pol = BoundaryPolicy(leaf_edges=2)
    out = contract_boundary(net, precision=9, policy=pol)
    cert = json.loads(json.dumps(out["certificate"]))
    assert replay_boundary(net, cert, precision=9, policy=pol)["valid"]
    tree = cert["tree"]
    if change == "mask":
        tree["terms"][1] = deepcopy(tree["terms"][0])
    elif change == "missing":
        tree["terms"].pop()
    elif change == "group":
        tree["groups"].reverse()
    elif change == "coefficient":
        tree["terms"][0]["coefficient"] = 2
    elif change == "child":
        tree["terms"][0]["children"][0]["value"] ^= 1
    elif change == "result":
        cert["result"] ^= 1
    elif change == "source":
        cert["source"]["source_sha256"] = "0" * 64
    else:
        cert["policy"].pop("verify_root")
    assert not replay_boundary(net, cert, precision=9, policy=pol)["valid"]


def test_failed_construction_or_verification_returns_no_answer(monkeypatch):
    net = cycle(12, 53)

    def forbidden(*a, **kw):
        raise AssertionError("root oracle called to supply the answer")

    monkeypatch.setattr(engine, "brute_contract", forbidden)
    expect = eliminate(net) % 512
    pol = BoundaryPolicy(verify_root=False)
    assert contract_boundary(net, precision=9, policy=pol)["result"] == expect
    for policy in (
        replace(pol, max_work=1),
        replace(pol, max_boundary_calls=1),
        replace(pol, max_certificate_bytes=8),
    ):
        out = contract_boundary(net, precision=9, policy=policy)
        assert out["status"] == "INCONCLUSIVE_RESOURCE_LIMIT" and "result" not in out
    monkeypatch.setattr(engine, "brute_contract", lambda *a, **kw: expect ^ 1)
    out = contract_boundary(net, precision=9)
    assert out["status"] == "INCONCLUSIVE_INVARIANT_FAILURE" and "result" not in out
    original = engine._child

    def corrupt(*args):
        child = original(*args)
        f = child.factors[0]
        return TensorNetwork(
            child.edges,
            (replace(f, table=tuple(x + 1 for x in f.table)), *child.factors[1:]),
        )

    monkeypatch.setattr(engine, "_child", corrupt)
    assert "result" not in contract_boundary(net, precision=9, policy=pol)


def test_nonshrinking_tapered_piece_refused():
    cnf = CNF.from_lists(12, [[i] for i in range(1, 13)])
    out = contract_boundary(
        from_cnf(cnf), precision=13, policy=BoundaryPolicy(piece_method="tapered")
    )
    assert out["status"] == "INCONCLUSIVE_NONSHRINKING_CHILD" and "result" not in out


def point_fixture():
    parent = describe_integer_network(
        from_cnf(CNF.from_lists(2, [[1, 2], [-1, 2]])),
        creation_precision=4,
        defining_polynomial=first_irreducible(5),
    )
    packing = construct_implicit_packing(
        parent.bipartite_edges(), r=4, a=1, max_work=100000
    )
    source = implicit_sparse_mode_source(packing)
    cert = make_point_modes(
        source,
        node=-1,
        precision=12,
        extension_degree=5,
        zeta=(1, 0, 0, 0, 0),
        max_tuples=1000,
        max_parent_wires=8,
    )
    return parent, cert


def test_compiled_children_provenance_and_replay():
    parent, cert = point_fixture()
    children = point.construct_recipe_children(parent, cert, (0,) * len(cert["modes"]))
    assert [c.group for c in children] == list(range(4))
    assert any(c.vertices == () for c in children)
    assert {
        v.entry.reference.creation_precision for c in children for v in c.vertices
    } == {4, 12}
    out = point.contract_recipe_point(parent, cert)
    assert out["result"] == (tuple(out["direct_parent_result"]),)
    saved = json.loads(json.dumps(out["certificate"]))
    assert point.replay_recipe_point(parent, cert, saved)
    saved["terms"][0]["groups"][0][2] = "wrong child hash"
    assert not point.replay_recipe_point(parent, cert, saved)


@pytest.mark.parametrize("fault", ["tuple", "group", "point", "precision", "cap"])
def test_recipe_point_is_fail_closed(fault, monkeypatch):
    parent, cert = point_fixture()
    if fault == "tuple":
        original = point.structural_tuples

        def broken(*args, **kw):
            rows = list(original(*args, **kw))
            return iter([rows[0], *rows[:-1]])

        monkeypatch.setattr(point, "structural_tuples", broken)
    elif fault == "group":
        original = point._construct
        monkeypatch.setattr(point, "_construct", lambda *args: original(*args)[:-1])
    elif fault == "point":
        monkeypatch.setattr(
            point,
            "independent_parent_point",
            lambda *a, **kw: {"valid": True, "result": [999]},
        )
    elif fault == "precision":
        cert["precision"] = 1
    out = point.contract_recipe_point(
        parent, cert, max_tuples=1 if fault == "cap" else 512
    )
    assert "result" not in out

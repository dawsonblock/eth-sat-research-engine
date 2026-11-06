"""Adversarial acceptance checks for the independent R9.8 child boundary."""

import json
import subprocess
import sys
from dataclasses import replace
from itertools import product
from pathlib import Path
from random import Random

import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.independent_r95.recipe_oracle import evaluate_reference
from veritas.research.parent_child_r98 import (
    Budget,
    ChildGraph,
    ExponentTuple,
    HermiteRecoveryCertificate,
    ModeSet,
    PointEvaluationCertificate,
    Policy,
    Semantics,
    construct_children,
    contract_scaled,
    from_described,
    verify_children,
)
from veritas.research.parent_child_r98.engine import (
    evaluate_point,
    leaf,
    verify_point_certificate,
    verify_recovery_certificate,
)
from veritas.research.parent_child_r98.independent import (
    reference_children,
)
from veritas.research.parent_child_r98.model import Refusal, canonical, decode
from veritas.research.parent_child_r98.modes import (
    TupleChecker,
    build_modes,
    verify_modes,
    weighted_count,
    weighted_tuples,
)
from veritas.research.parent_child_r98.packing import (
    audit_layout,
    construct_layout,
    preconditions,
)
from veritas.research.tapered_v4.source_recipes import (
    evaluate_source_entry,
    make_reference,
)
from veritas.research.tensor import Factor, TensorNetwork


def parent(n=1, degree=4, precision=5):
    vertices = []
    for i in range(n):
        vertices.append(Factor((i,), (-2 + i, 3 + i), "row:" + str(i)))
        vertices.append(Factor((i,), (4 - i, 5 - i), "col:" + str(i)))
    net = TensorNetwork(n, tuple(vertices))
    return from_described(
        describe_integer_network(
            net,
            creation_precision=precision,
            defining_polynomial=first_irreducible(degree),
        ),
        root_s=16,
        precision=precision,
    )


@pytest.fixture(scope="module")
def cross():
    p = parent(2)
    b = Budget()
    layout = construct_layout(p, budget=b)
    modes = build_modes(p, layout, -1, (1, 0, 0, 0), budget=b)
    beta = ExponentTuple(modes.content_digest, (1,))
    children = construct_children(p, layout, modes, beta, budget=b)
    return p, layout, modes, beta, children


def test_child_round_trip_and_independent_constructor(cross, monkeypatch):
    p, l, m, beta, cs = cross
    for child in cs:
        copy = ChildGraph.deserialize(child.serialize())
        assert copy == child and copy.content_digest == child.content_digest
    import veritas.research.parent_child_r98.constructor as production

    monkeypatch.setattr(
        production,
        "construct_children",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("production builder called")
        ),
    )
    assert reference_children(p, l, m, beta) == cs
    report = verify_children(p, l, m, beta, cs, budget=Budget())
    assert report["child_count"] == 64 and not report["all_source_shrink"]
    assert sum(c.edge_count for c in cs) == 2 * p.edge_count
    assert report["values"] == tuple(leaf(c.as_parent(p), Budget()) for c in cs)


@pytest.mark.parametrize(
    "attack",
    [
        "omit",
        "duplicate",
        "beta",
        "packet",
        "source",
        "bit_order",
        "coefficient",
        "precision",
        "point",
        "depth",
        "parent",
        "schedule",
        "equal_size",
    ],
)
def test_independent_child_rejects_mutations(cross, attack):
    p, l, m, beta, children = cross
    cs = list(children)
    c = cs[0]
    if attack == "omit":
        cs.pop()
    elif attack == "duplicate":
        cs[1] = cs[0]
    elif attack == "beta":
        cs[0] = replace(c, beta=ExponentTuple(m.content_digest, (0,)))
    elif attack in ("packet", "source", "bit_order"):
        maps = list(c.edge_map)
        row = list(maps[0])
        row[{"packet": 2, "source": 4, "bit_order": 5}[attack]] += 1
        maps[0] = tuple(row)
        cs[0] = replace(c, edge_map=tuple(maps))
    elif attack in ("coefficient", "precision"):
        vertices = list(c.vertices)
        j = next(i for i, v in enumerate(vertices) if v.side == "column")
        v = vertices[j]
        data = decode(v.tensor.description)
        if attack == "coefficient":
            data["data"][2][0][0][0][0] ^= 1
            ref = replace(v.tensor, description=canonical(data))
        else:
            # Consistently re-encode metadata so only the external semantics catches it.
            data["creation_precision"] += 1
            ref = replace(
                v.tensor,
                creation_precision=v.tensor.creation_precision + 1,
                description=canonical(data),
            )
            with pytest.raises(ValueError):
                replace(
                    c,
                    vertices=tuple(
                        vertices[:j] + [replace(v, tensor=ref)] + vertices[j + 1 :]
                    ),
                )
            return
        vertices[j] = replace(v, tensor=ref)
        cs[0] = replace(c, vertices=tuple(vertices))
    elif attack == "point":
        cs[0] = replace(c, node=1)
    elif attack == "depth":
        cs[0] = replace(c, depth=2)
    elif attack == "parent":
        cs[0] = replace(c, parent_digest="a" * 64)
    elif attack == "schedule":
        record = decode(c.schedule_bytes)
        record["paper_commit"] = "a" * 40
        cs[0] = replace(c, schedule_bytes=canonical(record))
    else:
        # A well-formed larger graph still belongs to a different parent/point.
        cs[1] = replace(c, group=1)
    with pytest.raises(ValueError):
        verify_children(p, l, m, beta, tuple(cs), budget=Budget())


def test_copied_digest_corruption_and_noncanonical_serialization(cross):
    child = cross[-1][0]
    obj = decode(child.serialize())
    obj["child"]["node"] *= -1
    with pytest.raises(ValueError, match="digest"):
        ChildGraph.deserialize(canonical(obj))
    with pytest.raises(ValueError, match="noncanonical"):
        ChildGraph.deserialize(json.dumps(decode(child.serialize()), indent=2).encode())
    with pytest.raises(ValueError):
        decode(b'{"a":1,"a":2}')


def test_duplicate_missing_and_shuffled_ports_rejected(cross):
    c = cross[-1][0]
    vertices = list(c.vertices)
    v = next(v for v in vertices if len(v.ports) > 1)
    j = vertices.index(v)
    for ports in ((v.ports[0],) * len(v.ports), v.ports[:-1]):
        with pytest.raises(ValueError):
            replace(
                c,
                vertices=tuple(
                    vertices[:j] + [replace(v, ports=ports)] + vertices[j + 1 :]
                ),
            )
    with pytest.raises(ValueError):
        replace(c, vertices=tuple(reversed(vertices)))


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "duplicate",
        "source",
        "target",
        "packet",
        "coefficient",
        "geometric",
        "weight",
        "boolean",
    ],
)
def test_mode_enumerator_rejects_changed_basis(cross, attack):
    p, l, m, _, _ = cross
    data = m.certificate
    if attack == "missing":
        data["modes"].pop()
    elif attack == "duplicate":
        data["modes"].append(data["modes"][0])
    elif attack == "coefficient":
        data["modes"][0]["rows"][0][1][0][0] ^= 2
    elif attack == "boolean":
        data["modes"][0]["source_group"] = True
    else:
        key = {
            "source": "source_group",
            "target": "target_group",
            "packet": "packet",
            "geometric": "exponent",
            "weight": "weight",
        }[attack]
        data["modes"][0][key] += 1
    with pytest.raises(ValueError):
        verify_modes(p, l, ModeSet(l.content_digest, canonical(data)), budget=Budget())


def test_weighted_stream_is_complete_including_structural_zeros(cross):
    _, _, m, _, _ = cross
    tuples = list(weighted_tuples(m, budget=Budget()))
    assert len(tuples) == 245 and tuples[-1].values == (244,)
    assert m.certificate["structural_tuple_count"] == 2
    for bad in (
        tuples[:-1],
        tuples[:-1] + [tuples[0]],
        tuples[:4] + [tuples[5]] + tuples[5:],
    ):
        verifier = TupleChecker(m, Budget())
        with pytest.raises(ValueError):
            for beta in bad:
                verifier.accept(beta)
            verifier.finish()
    for weights in ((), (1,), (2, 3), (1, 2, 3)):
        for p in (1, 2, 7):
            brute = sum(
                sum(x * w for x, w in zip(xs, weights)) < p
                for xs in product(range(p), repeat=len(weights))
            )
            assert weighted_count(weights, p, 10000) == brute
    with pytest.raises(Refusal, match="complete weighted"):
        list(weighted_tuples(m, budget=Budget(Policy(max_tuples=10))))


@pytest.mark.parametrize(
    "attack", ["duplicate", "omitted", "slot", "orientation", "labels"]
)
def test_actual_packet_audit(cross, attack):
    p, l, _, _, _ = cross
    src = l.source
    if attack == "duplicate":
        src["packets"][1]["occupied_slots"][0][1] = 0
    elif attack == "omitted":
        src["packets"].pop()
    elif attack == "slot":
        src["packets"][0]["occupied_slots"].append(
            src["packets"][0]["occupied_slots"][0]
        )
    elif attack == "orientation":
        src["packets"][1]["occupied_slots"][0][0] ^= 1
    else:
        src["row_labels"].pop("0")
    with pytest.raises(ValueError):
        audit_layout(p, replace(l, source_bytes=canonical(src)))


def test_small_source_and_overloaded_scaled_layout_are_never_qualified(cross):
    p, l, _, _, _ = cross
    report = audit_layout(p, l)
    assert not report["source_eligible"] and not report["group_load_bound_met"]
    assert not report["packet_bound_met"]
    for s in (12, 14, 16):
        numeric = preconditions(replace(p, root_s=s))
        assert numeric["schedule"]["u"] == 0
        assert numeric["status"] == "INCONCLUSIVE_SOURCE_SCHEDULE"
    with pytest.raises(ValueError):
        replace(p, semantics=Semantics.SOURCE_QUALIFIED)


@pytest.mark.parametrize("degree", [2, 3, 5])
def test_creation_precision_lift_is_not_re_evaluation(degree):
    f = first_irreducible(degree)
    # A row affine entry 1 - 3 = -2 is created mod 4 as 2; later it stays 2.
    ref = make_reference(
        kind="packet",
        arity=2,
        creation_precision=2,
        defining_polynomial=f,
        jet_length=1,
        data=[[0], [1], [[[[3] + [0] * (degree - 1)]]], [], []],
    )
    assert evaluate_source_entry(ref, (0, 1), precision=9)["result"] == (
        (2,) + (0,) * (degree - 1),
    )
    assert evaluate_reference(ref, (0, 1), precision=9) == ((2,) + (0,) * (degree - 1),)
    rng = Random(9800 + degree)
    for _ in range(12):
        pc = rng.randrange(2, 7)
        value = rng.randrange(1 << pc)
        ref = make_reference(
            kind="dense",
            arity=0,
            creation_precision=pc,
            defining_polynomial=f,
            jet_length=1,
            data=[[[value] + [0] * (degree - 1)]],
        )
        before = evaluate_source_entry(ref, (), precision=pc)["result"]
        assert evaluate_source_entry(ref, (), precision=pc + 10)["result"] == before
        assert evaluate_reference(ref, (), precision=pc + 10) == before


def test_empty_target_source_and_zero_power_conventions():
    for beta, expected in ((0, 1), (1, 0)):
        for data in ([[], [], [], [[beta, []]], []], [[], [], [], [], [[beta, []]]]):
            ref = make_reference(
                kind="packet",
                arity=0,
                creation_precision=3,
                defining_polynomial=7,
                jet_length=1,
                data=data,
            )
            assert evaluate_source_entry(ref, (), precision=5)["result"] == (
                (expected, 0),
            )
            assert evaluate_reference(ref, (), precision=5) == ((expected, 0),)


@pytest.fixture(scope="module")
def single_point():
    p = parent()
    budget = Budget()
    l = construct_layout(p, budget=budget)
    m = build_modes(p, l, -1, (1, 0, 0, 0), budget=budget)
    value, cert, _ = evaluate_point(p, l, m, budget=budget, capture=True)
    return p, l, m, value, cert


def test_point_verifier_does_not_call_production_constructor(single_point, monkeypatch):
    p, l, m, value, cert = single_point
    from veritas.research.parent_child_r98 import engine

    monkeypatch.setattr(
        engine,
        "construct_children",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("production called")),
    )
    assert verify_point_certificate(p, l, m, cert)["result"] == value


@pytest.mark.parametrize(
    "attack",
    [
        "drop_beta",
        "duplicate_beta",
        "missing_group",
        "wrong_value",
        "compensating_values",
        "hash",
        "precision",
        "pin",
    ],
)
def test_point_certificate_tampering(single_point, attack):
    p, l, m, _, cert = single_point
    data = decode(cert.payload)
    if attack == "drop_beta":
        data["terms"].pop()
    elif attack == "duplicate_beta":
        data["terms"].append(data["terms"][0])
    elif attack == "missing_group":
        data["terms"][0]["groups"].pop()
    elif attack in ("wrong_value", "compensating_values"):
        data["terms"][0]["groups"][1][-1][0][0] = 3
        if attack == "compensating_values":
            data["terms"][0]["groups"][2][-1][0][0] = pow(3, -1, 2 ** data["precision"])
    elif attack == "hash":
        data["terms"][0]["groups"][0][2] = "a" * 64
    elif attack == "precision":
        data["precision"] -= 1
    else:
        data["paper"]["commit"] = "a" * 40
    result = verify_point_certificate(
        p, l, m, PointEvaluationCertificate(canonical(data))
    )
    assert "result" not in result


def test_recovery_and_no_oracle_substitution(monkeypatch):
    p = parent()
    result = contract_scaled(p, levels=1, strategy="scaled_singletons")
    assert result["result"] == ((7, 0, 0, 0),)
    cert = HermiteRecoveryCertificate(canonical(result["hermite_recovery"]))
    l = construct_layout(p, strategy="scaled_singletons", budget=Budget())
    assert verify_recovery_certificate(p, l, cert)["result"] == result["result"]
    for key in ("result", "point_rows", "coefficient_precisions", "guard_bits"):
        data = decode(cert.payload)
        if key == "result":
            data[key][0] ^= 1
        elif key == "point_rows":
            data[key][0][0] *= -1
        elif key == "coefficient_precisions":
            data[key]["-1"][0] -= 1
        else:
            data[key] += 1
        assert "result" not in verify_recovery_certificate(
            p, l, HermiteRecoveryCertificate(canonical(data))
        )
    from veritas.research.parent_child_r98 import engine

    monkeypatch.setattr(engine, "leaf", lambda *a, **k: ((0, 0, 0, 0),))
    bad = contract_scaled(p, levels=1, strategy="scaled_singletons")
    assert "result" not in bad and "child contraction" in bad["reason"]


def test_two_level_generated_recursion_preserves_creation():
    result = contract_scaled(
        parent(), levels=2, strategy="scaled_singletons", policy=Policy(max_seconds=240)
    )
    assert result["result"] == ((7, 0, 0, 0),)
    assert result["ledger"]["maximum_depth"] == 2
    assert result["ledger"]["actual_calls"] == 124929
    assert result["ledger"]["point_evaluations"] == 1952
    assert result["ledger"]["nonshrinking_children"] == 1952
    assert not result["source_qualified"] and not result["theorem_mode_enabled"]


def test_all_resource_limits_fail_closed():
    for policy in (
        Policy(max_calls=1),
        Policy(max_work=1),
        Policy(max_precision=10),
        Policy(max_edges=1),
    ):
        result = contract_scaled(
            parent(), levels=2, strategy="scaled_singletons", policy=policy
        )
        assert (
            "result" not in result and result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
        )


def test_external_cli_and_stored_digest(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cert = tmp_path / "point.json"
    common = [sys.executable, "-m", "veritas.research.parent_child_r98"]
    fixture = root / "examples/r98_one_edge.json"
    proc = subprocess.run(
        [*common, "point", str(fixture), "--certificate", str(cert)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = subprocess.run(
        [*common, "verify-point", str(fixture), "--certificate", str(cert)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    obj = decode(cert.read_bytes())
    obj["certificate"]["result"][0][0] ^= 1
    cert.write_bytes(canonical(obj))
    proc = subprocess.run(
        [*common, "verify-point", str(fixture), "--certificate", str(cert)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0 and "digest mismatch" in proc.stdout


@pytest.mark.parametrize("edges", [12, 14, 16])
def test_finite_boundary_signed_repeated_and_isolated_factors(edges):
    from veritas.research.finite_reductions import BoundaryPolicy, contract_boundary
    from veritas.research.paper_verification.boundary_identity import (
        verify_boundary_tree,
    )
    from veritas.research.tensor import brute_contract, eliminate

    rng = Random(98000 + edges)
    perm = list(range(edges))
    rng.shuffle(perm)
    # Repeated tensor values are separate factor occurrences. Nullary vertices
    # contribute their scalar, even when they have no incident edge.
    factors = [
        Factor((perm[(i + 1) % edges], perm[i]), (-2, 3, 1, -1), "repeated")
        for i in range(edges)
    ]
    factors.extend((Factor((), (-3,), "isolated"), Factor((), (2,), "isolated")))
    rng.shuffle(factors)
    net = TensorNetwork(edges, tuple(factors))
    expected = brute_contract(net, max_edges=16) % (1 << 41)
    assert eliminate(net, modulus=1 << 41) == expected
    policy = BoundaryPolicy(leaf_edges=3, verify_root=False)
    result = contract_boundary(net, precision=41, policy=policy)
    assert result.get("result") == expected, result
    checked = verify_boundary_tree(
        net, result["certificate"], precision=41, policy=policy
    )
    assert checked.get("result") == expected

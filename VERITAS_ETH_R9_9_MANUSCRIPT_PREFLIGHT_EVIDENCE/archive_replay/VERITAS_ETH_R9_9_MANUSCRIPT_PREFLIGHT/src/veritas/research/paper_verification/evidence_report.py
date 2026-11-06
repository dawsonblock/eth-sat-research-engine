"""Complete finite grid audit. The parent oracle can only accept or reject a child sum."""

from time import monotonic
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.extension_lagrange import (
    interpolate_newton,
    evaluate_polynomial,
)
from veritas.research.eth_interpolation.source_hermite import (
    make_source_tapered_plan,
    reconstruct_source_tapered,
)
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing,
    implicit_sparse_mode_source,
)
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.finite_reductions.boundary import _bytes, _digest
from veritas.research.tensor import from_cnf, brute_contract
from .child_identity import construct_reduction, verify_reduction, SCOPE
from .hermite_checker import check_functional, recover_reference


def grid_certificate(cnf, *, s, r, a, u, submitted=None):
    if sum(map(len, cnf.clauses)) > 8 or cnf.n > 16 or len(cnf.clauses) > 32:
        raise ValueError("bounded original CNF required")
    if any(type(x) is not int for x in (s, r, a, u)) or not 2 <= r <= 64:
        raise ValueError("unsupported parameters")
    deadline = monotonic() + 300
    net = from_cnf(cnf)
    p = cnf.n + 1
    f = first_irreducible(5)
    parent = describe_integer_network(net, creation_precision=p, defining_polynomial=f)
    plan = make_source_tapered_plan(M=net.edges, a=a, u=u, p=p, max_precision_bits=1024)
    check_functional(plan)
    order = plan.degree_bound + 1
    expected = len(plan.nodes) * order
    envelope = {
        "schema": "VERITAS_R97_GRID_V1",
        "scope": SCOPE,
        "cnf": cnf.as_dict(),
        "s": s,
        "r": r,
        "a": a,
        "u": u,
        "p": p,
        "degree": plan.degree_bound,
        "total_points": expected,
    }
    if submitted is not None:
        if (
            set(submitted) != set(envelope) | {"points", "result"}
            or any(_bytes(submitted[k]) != _bytes(v) for k, v in envelope.items())
            or len(submitted["points"]) != expected
        ):
            raise ValueError("submitted grid header or point coverage differs")
    packing = construct_implicit_packing(
        parent.bipartite_edges(), r=r, a=a, max_work=3_000_000
    )
    source = implicit_sparse_mode_source(packing, max_work=1_000_000)
    points = []
    hashes = set()
    terms = groups = max_child = reference_work = 0
    jets = {}
    sizes = {}
    for node in plan.nodes:
        ring = ExtensionRing(node.precision_bits, f)
        zs = distinct_residue_points(ring, order, max_points=32)
        samples = []
        for z in zs:
            if monotonic() > deadline:
                raise TimeoutError("grid deadline")
            modes = make_point_modes(
                source,
                node=node.t,
                precision=ring.p,
                extension_degree=5,
                zeta=z,
                max_tuples=512,
                max_parent_wires=8,
            )
            kwargs = {"s": s, "depth": 0, "u": u, "p": p}
            piece = (
                construct_reduction(parent, modes, **kwargs)
                if submitted is None
                else submitted["points"][len(points)]
            )
            verified = verify_reduction(parent, modes, piece, **kwargs)
            if "result" not in verified:
                raise ValueError(verified["reason"])
            # The value comes from the independently contracted children, after the equality check.
            samples.append(verified["result"][0])
            points.append(piece)
            reference_work += verified["reference_work_units"]
            terms += verified["tuples"]
            groups += verified["group_values_checked"]
            for term in piece["child_sum"]["terms"]:
                for _, edges, digest, _ in term["groups"]:
                    hashes.add((digest, node.precision_bits))
                    max_child = max(max_child, edges)
        polynomial = interpolate_newton(ring, zs, samples, max_points=32)
        if any(
            evaluate_polynomial(ring, polynomial, z) != y for z, y in zip(zs, samples)
        ):
            raise ValueError(
                "interpolated polynomial does not evaluate to supplied child sums"
            )
        jets[node.t] = polynomial[: node.multiplicity]
        sizes[node.t] = (ring.p,) * len(jets[node.t])
    recovered = []
    for i in range(5):
        data = {t: tuple(y[i] for y in ys) for t, ys in jets.items()}
        value = recover_reference(plan, data, sizes)
        if (
            reconstruct_source_tapered(plan, data, coefficient_precisions=sizes)
            != value
        ):
            raise ValueError("recovery disagreement")
        recovered.append(value)
    if recovered != [brute_contract(net, max_edges=8, modulus=1 << p), 0, 0, 0, 0]:
        raise ValueError("zero-point contraction mismatch")
    if submitted is not None and _bytes(recovered) != _bytes(submitted["result"]):
        raise ValueError("submitted recovery differs")
    if monotonic() > deadline:
        raise TimeoutError("grid deadline")
    envelope.update(points=points, result=recovered)
    return envelope, {
        "status": "FINITE_GRID_VERIFIED",
        "points_checked": len(points),
        "points_total": expected,
        "tuples": terms,
        "group_contractions": groups,
        "distinct_group_descriptors_with_precision": len(hashes),
        "maximum_child_wires": max_child,
        "independent_reference_work": reference_work,
        "newton_interpolations": len(plan.nodes),
        "coordinate_recoveries": 5,
        "source_active": False,
        "result": recovered,
        "certificate_sha256": _digest(envelope),
    }

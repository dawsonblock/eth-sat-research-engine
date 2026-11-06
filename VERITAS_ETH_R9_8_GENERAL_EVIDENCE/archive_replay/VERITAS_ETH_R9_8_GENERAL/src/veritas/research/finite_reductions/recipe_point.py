"""Finite point expansion with executable creation-time recipes in every group.

The supplied mode certificate determines the packing, point and precision.
The per-term constructor and the complete sum have distinct postconditions.
"""

from dataclasses import asdict, dataclass
from itertools import product

from veritas.research.eth_recursive_contraction_v39.point_children import (
    _build_point_children_checked,
    _ring_for,
)
from veritas.research.eth_recursive_contraction_v39.structural_tuples import (
    structural_tuples,
)
from veritas.research.eth_recursive_contraction_v39.tuple_stream_check import (
    TupleStreamVerifier,
    independently_valid_tuple,
)
from veritas.research.independent_r82.point_mode_oracle import (
    independent_parent_point,
    verify_point_mode_action,
)
from veritas.research.independent_r82.pruning import audit_finite_pruning
from veritas.research.tapered_v4.child_recipe_check import (
    verify_constructed_child_recipes,
)
from veritas.research.tapered_v4.source_recipe_bridge import (
    source_reference_from_created,
)
from veritas.research.tapered_v4.source_recipes import (
    Arithmetic,
    CompiledEntry,
    EntryBudget,
    EntryLimits,
    compile_entry,
    evaluate_compiled,
)
from .boundary import _bytes, _digest, _source_identity


@dataclass(frozen=True)
class RecipeVertex:
    side: str
    label: str
    ports: tuple
    entry: CompiledEntry


@dataclass(frozen=True)
class RecipeChild:
    group: int
    edges: int
    vertices: tuple[RecipeVertex, ...]

    def descriptor(self):
        return {
            "group": self.group,
            "edges": self.edges,
            "vertices": [
                [
                    v.side,
                    v.label,
                    v.ports,
                    v.entry.reference.creation_precision,
                    v.entry.reference.description_sha256,
                ]
                for v in self.vertices
            ],
        }


def _compile_child(group, network, budget):
    vertices = []
    for vertex in network.vertices:
        budget.tick()
        reference = source_reference_from_created(vertex.tensor, limits=budget.limits)
        vertices.append(
            RecipeVertex(
                vertex.side,
                vertex.label,
                vertex.ports,
                compile_entry(reference, budget),
            )
        )
    return RecipeChild(group, network.edges, tuple(vertices))


def _admit_point(parent, modes, budget):
    ring, source = _ring_for(parent, modes, max_parent_wires=8, _tuple_work=budget.tick)
    if ring.length != 1 or not 2 <= source["r"] <= 64:
        raise ValueError("finite scalar point and radix 2..64 required")
    action = verify_point_mode_action(source, modes, max_work=1_000_000, timeout_s=30)
    if action.get("valid") is not True:
        raise ValueError("independent mode action check: " + str(action.get("status")))
    budget.tick()
    return ring, source


def _construct(parent, modes, beta, ring, source, budget):
    # The tuple-set verifier in the caller also checks completeness across calls.
    if not independently_valid_tuple(
        beta, modes["modes"], ring.base.p, on_step=budget.tick
    ):
        raise ValueError("tuple violates structural constraints")
    occupied = _build_point_children_checked(parent, modes, beta, ring, source)
    verify_constructed_child_recipes(
        parent, source, modes, beta, occupied, ring, on_step=budget.tick
    )
    groups = {c.group: c.network for c in occupied}
    if len(groups) != len(occupied) or any(g not in range(source["r"]) for g in groups):
        raise ValueError("duplicate or invalid group")
    for exponent, mode in zip(beta, modes["modes"]):
        if exponent and (
            mode["source_group"] not in groups or mode["target_group"] not in groups
        ):
            raise ValueError("required mode endpoint absent")
    return tuple(
        _compile_child(g, groups[g], budget) if g in groups else RecipeChild(g, 0, ())
        for g in range(source["r"])
    )


def construct_recipe_children(parent, mode_certificate, beta, *, limits=EntryLimits()):
    """Return one immutable executable child per radix group for this admitted tuple."""
    budget = EntryBudget(limits)
    ring, source = _admit_point(parent, mode_certificate, budget)
    return _construct(parent, mode_certificate, beta, ring, source, budget)


def _value(child, ring, budget):
    if child.edges > 8:
        raise ValueError("finite recipe point child exceeds eight wires")
    arithmetic = Arithmetic(ring, budget)
    # Cache entries by their local bits only for the lifetime of this group.
    tables = [dict() for _ in child.vertices]
    total = ring.zero
    for bits in product((0, 1), repeat=child.edges):
        budget.tick()
        term = ring.one
        for vertex, table in zip(child.vertices, tables):
            local = tuple(bits[i] for i in vertex.ports)
            if local not in table:
                table[local] = evaluate_compiled(
                    vertex.entry, local, ring.base.p, budget
                )
            term = arithmetic.mul(term, table[local])
        total = arithmetic.add(total, term)
    return total


def contract_recipe_point(
    parent, mode_certificate, *, limits=EntryLimits(), max_tuples=512
):
    """Accept only a complete sum that also matches an independent half-edge calculation."""
    budget = EntryBudget(limits)
    try:
        if type(max_tuples) is not int or not 1 <= max_tuples <= 4096:
            raise ValueError("tuple budget must be in 1..4096")
        identity = _source_identity()
        ring, source = _admit_point(parent, mode_certificate, budget)
        modes = mode_certificate["modes"]
        verifier = TupleStreamVerifier(
            modes, ring.base.p, max_tuples=max_tuples, on_step=budget.tick
        )
        if verifier.expected_count != mode_certificate["structural_tuple_count"]:
            raise ValueError("independent tuple count differs")
        arithmetic = Arithmetic(ring, budget)
        terms = []
        total = ring.zero
        for beta in structural_tuples(
            modes, ring.base.p, max_tuples=max_tuples, _on_step=budget.tick
        ):
            verifier.accept(beta)
            children = _construct(parent, mode_certificate, beta, ring, source, budget)
            if tuple(child.group for child in children) != tuple(range(source["r"])):
                raise ValueError("incomplete ordered group set")
            term = ring.one
            witnesses = []
            for child in children:
                value = _value(child, ring, budget)
                term = arithmetic.mul(term, value)
                witnesses.append(
                    [child.group, child.edges, _digest(child.descriptor()), value]
                )
            total = arithmetic.add(total, term)
            terms.append({"beta": tuple(beta), "groups": witnesses, "product": term})
        verifier.finish()
        pruning = audit_finite_pruning(
            modes,
            ring.base.p,
            emitted_tuples=[t["beta"] for t in terms],
            max_vectors=100_000,
        )
        if pruning.get("valid") is not True:
            raise ValueError("independent pruning audit: " + str(pruning.get("status")))
        direct = independent_parent_point(
            parent,
            source,
            mode_certificate,
            max_edges=8,
            max_work=5_000_000,
            timeout_s=30,
        )
        if direct.get("valid") is not True or total != (
            tuple(direct.get("result", ())),
        ):
            raise ValueError("complete recipe sum failed direct point comparison")
        parent_id = _digest(_compile_child(-1, parent, budget).descriptor())
        cert = {
            "schema": "FINITE_RECIPE_POINT_V1",
            "parent_sha256": parent_id,
            "packing_sha256": _digest(source),
            "mode_sha256": _digest(mode_certificate),
            "source": identity,
            "entry_policy": asdict(limits),
            "max_tuples": max_tuples,
            "point": [mode_certificate["node"], mode_certificate["zeta"]],
            "p": ring.base.p,
            "extension_polynomial": ring.base.f,
            "groups_per_tuple": source["r"],
            "terms": terms,
            "value": total,
        }
        budget.tick()
        return {
            "status": "EXACT_CHECKED_FINITE_RECIPE_POINT",
            "result": total,
            "certificate": cert,
            "direct_parent_result": direct["result"],
            "ledger": budget.ledger(),
        }
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
        RuntimeError,
        OSError,
        MemoryError,
    ) as exc:
        return {
            "status": getattr(exc, "status", "INCONCLUSIVE_RECIPE_POINT"),
            "reason": str(exc),
            "ledger": budget.ledger(),
        }


def replay_recipe_point(
    parent, mode_certificate, saved, *, limits=EntryLimits(), max_tuples=512
):
    """Regenerate every child, tuple, group product and independent parent value."""
    if not isinstance(saved, dict) or saved.get("schema") != "FINITE_RECIPE_POINT_V1":
        return False
    regenerated = contract_recipe_point(
        parent, mode_certificate, limits=limits, max_tuples=max_tuples
    )
    try:
        return "certificate" in regenerated and _bytes(saved) == _bytes(
            regenerated["certificate"]
        )
    except (ValueError, TypeError, RecursionError):
        return False

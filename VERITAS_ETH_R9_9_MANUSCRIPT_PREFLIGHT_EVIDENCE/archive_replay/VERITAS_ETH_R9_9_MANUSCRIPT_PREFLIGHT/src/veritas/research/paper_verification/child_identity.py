"""Construct and independently evaluate bounded instances of eq:tensor-recursion-identity."""

from dataclasses import asdict
from time import monotonic

from veritas.research.finite_reductions.boundary import (
    _bytes,
    _digest,
    _source_identity,
)
from veritas.research.finite_reductions.recipe_point import (
    _admit_point,
    _compile_child,
    _construct,
    contract_recipe_point,
)
from veritas.research.tapered_v4.source_recipes import EntryLimits, EntryBudget
from veritas.research.independent_r82.point_mode_oracle import independent_parent_point
from veritas.research.independent_r82.pruning import audit_finite_pruning
from veritas.research.independent_r95.recipe_oracle import (
    ReferenceArithmetic,
    contract_reference_factors,
)
from veritas.research.eth_recursive_contraction_v39.tuple_stream_check import (
    TupleStreamVerifier,
)
from .exact_parameters import check_schedule, hermite_parameters
from .source_registry import source_registry
from .packing_checker import check_packing

LABEL = "eq:tensor-recursion-identity"
SCOPE = "FINITE_PAPER_IDENTITY_SCALED_PARAMETERS"
LIMIT = 512


def _header(parent, modes, s, depth, u, p):
    source = modes["d3_certificate"]
    pars = hermite_parameters(parent.edges, source["a"], u, p)
    node = next((x for x in pars["nodes"] if x[0] == modes["node"]), None)
    if node is None or node[-1] != modes["precision"]:
        raise ValueError("wrong tapered node or precision")
    q = check_schedule(
        s, parent.edges, max(len(v.ports) for v in parent.vertices), depth
    )
    source_record = source_registry()
    return {
        "schema": "VERITAS_R97_POINT_REDUCTION_V1",
        "scope": SCOPE,
        "source_active_execution": False,
        "paper_source_sha256": source_record["files"]["quantitative-contraction.tex"],
        "equation": LABEL,
        "statement_sha256": source_record["labels"][LABEL]["statement_sha256"],
        "s": s,
        "depth": depth,
        "scheduled": q,
        "used": {
            "r": source["r"],
            "a": source["a"],
            "u": u,
            "p": p,
            "child_precision": node[-1],
            "multiplicity": node[2],
            "interpolation_scale": node[3],
        },
        "mode_certificate_sha256": _digest(modes),
    }


def construct_reduction(parent, modes, *, s, depth, u, p):
    record = _header(parent, modes, s, depth, u, p)
    result = contract_recipe_point(parent, modes, max_tuples=LIMIT)
    if "result" not in result:
        raise ValueError(result["reason"])
    return dict(
        record,
        mode_certificate=modes,
        child_sum=result["certificate"],
        independent_parent_value=result["direct_parent_result"],
    )


def verify_reduction(parent, expected_modes, saved, *, s, depth, u, p):
    """Check the submitted complete stream without calling the production point evaluator."""
    try:
        header = _header(parent, expected_modes, s, depth, u, p)
        fields = {"mode_certificate", "child_sum", "independent_parent_value"}
        if type(saved) is not dict or set(saved) != set(header) | fields:
            raise ValueError("certificate fields")
        if any(_bytes(saved[k]) != _bytes(v) for k, v in header.items()) or _bytes(
            saved["mode_certificate"]
        ) != _bytes(expected_modes):
            raise ValueError("external request or source differs")
        claimed = saved["child_sum"]
        budget = EntryBudget(EntryLimits(max_seconds=60, max_work=15_000_000))
        ring, source = _admit_point(parent, expected_modes, budget)
        packing = check_packing(source, parent.bipartite_edges())
        binding = {
            "schema": "FINITE_RECIPE_POINT_V1",
            "parent_sha256": _digest(_compile_child(-1, parent, budget).descriptor()),
            "packing_sha256": _digest(source),
            "mode_sha256": _digest(expected_modes),
            "source": _source_identity(),
            "entry_policy": asdict(EntryLimits()),
            "max_tuples": LIMIT,
            "point": [expected_modes["node"], expected_modes["zeta"]],
            "p": ring.base.p,
            "extension_polynomial": ring.base.f,
            "groups_per_tuple": source["r"],
        }
        if set(claimed) != set(binding) | {"value", "terms"} or any(
            _bytes(claimed[k]) != _bytes(v) for k, v in binding.items()
        ):
            raise ValueError("child sum dependency differs")
        modes = expected_modes["modes"]
        stream = TupleStreamVerifier(
            modes, ring.base.p, max_tuples=LIMIT, on_step=budget.tick
        )
        terms = claimed["terms"]
        if (
            type(terms) is not list
            or len(terms) != stream.expected_count
            or len(terms) != expected_modes["structural_tuple_count"]
        ):
            raise ValueError("incomplete term set")
        if any(type(term.get("beta")) not in (list, tuple) for term in terms):
            raise ValueError("invalid serialized exponent vector")
        pruning = audit_finite_pruning(
            modes,
            ring.base.p,
            emitted_tuples=[tuple(v["beta"]) for v in terms],
            max_vectors=100_000,
        )
        if pruning.get("valid") is not True:
            raise ValueError("unproved pruning")
        ar = ReferenceArithmetic(ring.base.p, ring.base.f, 1, 25_000_000)
        total = ar.zero
        count = 0
        for term in terms:
            if set(term) != {"beta", "groups", "product"}:
                raise ValueError("term fields")
            beta = tuple(term["beta"])
            stream.accept(beta)
            children = _construct(parent, expected_modes, beta, ring, source, budget)
            if len(term["groups"]) != source["r"] or len(children) != source["r"]:
                raise ValueError("missing group")
            value = ar.one
            for g, (child, record) in enumerate(zip(children, term["groups"])):
                budget.tick()
                refs = [(v.ports, v.entry.reference) for v in child.vertices]
                actual = contract_reference_factors(child.edges, refs, ar)
                if child.group != g or _bytes(record) != _bytes(
                    [g, child.edges, _digest(child.descriptor()), actual]
                ):
                    raise ValueError("group recipe, occurrence or value differs")
                value = ar.mul(value, actual)
                count += 1
            if _bytes(value) != _bytes(term["product"]):
                raise ValueError("wrong product")
            total = ar.add(total, value)
        stream.finish()
        direct = independent_parent_point(
            parent,
            source,
            expected_modes,
            max_edges=8,
            max_work=5_000_000,
            timeout_s=30,
        )
        if (
            direct.get("valid") is not True
            or _bytes(direct["result"]) != _bytes(total[0])
            or (
                _bytes(saved["independent_parent_value"]) != _bytes(total[0])
                or _bytes(claimed["value"]) != _bytes(total)
            )
        ):
            raise ValueError("parent reconstruction differs")
        budget.tick()
        return {
            "status": "VERIFIED_FINITE_POINT_IDENTITY",
            "result": total,
            "tuples": len(terms),
            "group_values_checked": count,
            "reference_work_units": ar.used,
            "actual_packing": packing,
            "scope": SCOPE,
            "theorem_qualified": False,
        }
    except (
        OSError,
        ArithmeticError,
        RuntimeError,
        MemoryError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
    ) as exc:
        return {"status": "INCONCLUSIVE_OR_INVALID_REDUCTION", "reason": str(exc)}

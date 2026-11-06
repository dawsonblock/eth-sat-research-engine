"""Complete point modes for finite a=u=1 singleton packet layouts.

Unlike the constant-deformation path, this module admits nonzero interpolation
values. Every cross-group singleton has tile quotient j=0: its b=0 mode is
retained exactly when its target coefficient is nonzero, while every b>0
source form is identically zero. No nonzero mode or weighted tuple is removed
to meet a budget. The independent verifier evaluates the rational shifted
Cauchy polynomial using a separate implementation of the extension ring.
"""

from math import comb

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value
from veritas.research.independent_r82.point_mode_oracle import (
    _evaluate_shifted,
    _IndependentExtension,
    _Meter,
    shifted_cauchy_polynomial,
)

from .model import ModeSet, Refusal, Semantics, canonical
from .modes import weighted_count
from .packing import audit_layout


_FIELDS = {
    "d3_certificate", "node", "precision", "jet_length", "extension_degree",
    "irreducible_polynomial", "zeta", "local", "cross_pairs", "modes",
    "mode_tuple_count",
}


def _admit(parent, layout, node, zeta, budget):
    audit_layout(parent, layout)
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("general singleton modes require finite scaled semantics")
    if (layout.a, layout.u) != (1, 1):
        raise ValueError("general singleton modes require a=u=1")
    if type(node) is not int or node not in (-1, 1):
        raise ValueError("general singleton modes require node -1 or +1")
    if parent.edge_count > budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general mode parent edge cap")
    precision = parent.precision + 64 * parent.edge_count
    if precision > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general point precision cap")
    degree = parent.defining_polynomial.bit_length() - 1
    if not 2 <= degree <= 12:
        raise Refusal(
            "INCONCLUSIVE_RESOURCE_LIMIT", "general point ring supports degree 2..12"
        )
    if (
        type(zeta) not in (tuple, list)
        or len(zeta) != degree
        or any(type(x) is not int or not 0 <= x < 1 << precision for x in zeta)
    ):
        raise ValueError("noncanonical general interpolation coordinates")
    for packet in layout.source["packets"]:
        budget.tick()
        if len(packet["occupied_slots"]) != 1:
            raise ValueError("general point modes require singleton packets")
    return precision, degree


def _complete_count(number, precision, budget):
    # For k weight-one modes, stars-and-bars counts |beta| < p exactly.
    # Refuse before any child construction or expansion of a gigantic stream.
    count = comb(precision + number - 1, number)
    budget.tick(number + 1)
    if count > budget.policy.max_tuples:
        raise Refusal(
            "INCONCLUSIVE_RESOURCE_LIMIT",
            "complete general weighted tuple count exceeds policy",
        )
    return count


def build_general_modes(parent, layout, node, zeta, *, budget):
    """Generate every nonzero singleton mode, then independently verify it."""
    precision, degree = _admit(parent, layout, node, zeta, budget)
    ring = ExtensionRing(
        precision, parent.defining_polynomial,
        max_precision_bits=budget.policy.max_precision,
    )
    zeta = tuple(zeta)
    source = layout.source
    local, crosses, modes = [], [], []
    coefficients = {}
    for packet_id, packet in enumerate(source["packets"]):
        budget.tick()
        slot, edge = packet["occupied_slots"][0]
        row, column = source["edges"][edge]
        target = source["row_labels"][str(row)][0]
        origin = source["column_labels"][str(column)][0]
        if slot not in coefficients:
            coefficients[slot] = cauchy_point_value(2, node, ring, slot, slot, zeta)
            budget.tick(16 * degree**2)
        coefficient = coefficients[slot]
        if target == origin:
            if coefficient != ring.zero:
                local.append([edge, edge, [list(coefficient)]])
        else:
            crosses.append([edge, edge])
            if coefficient != ring.zero:
                if ring.valuation(coefficient) < 1:
                    raise ValueError("singleton cross mode lacks its weight-one divisibility")
                modes.append({
                    "packet": packet_id,
                    "tile_residue": slot,
                    "exponent": 0,
                    "weight": 1,
                    "source_group": origin,
                    "target_group": target,
                    "rows": [[edge, [list(coefficient)]]],
                    "column_terms": [[edge, 1]],
                })
    count = _complete_count(len(modes), precision, budget)
    record = {
        "d3_certificate": source,
        "node": node,
        "precision": precision,
        "jet_length": 1,
        "extension_degree": degree,
        "irreducible_polynomial": parent.defining_polynomial,
        "zeta": list(zeta),
        "local": local,
        "cross_pairs": sorted(crosses),
        "modes": modes,
        "mode_tuple_count": count,
    }
    result = ModeSet(layout.content_digest, canonical(record))
    verify_general_modes(parent, layout, result, budget=budget)
    return result


def verify_general_modes(parent, layout, modes, *, budget):
    """Independently reconstruct the full rational singleton mode action.

    This verifier does not call the production builder, Cauchy evaluator,
    child constructor, or tensor-entry evaluator. The complete tuple count is
    rechecked by a generating-function dynamic program, not stars-and-bars.
    """
    if modes.layout_digest != layout.content_digest:
        raise ValueError("general mode layout binding mismatch")
    record = modes.certificate
    if type(record) is not dict or set(record) != _FIELDS:
        raise ValueError("general mode certificate fields")
    precision, degree = _admit(
        parent, layout, record["node"], record["zeta"], budget
    )
    if any(type(record[key]) is not int for key in (
        "precision", "jet_length", "extension_degree", "irreducible_polynomial",
        "mode_tuple_count",
    )):
        raise ValueError("general mode metadata requires integers")
    if (
        record["precision"] != precision
        or record["jet_length"] != 1
        or record["extension_degree"] != degree
        or record["irreducible_polynomial"] != parent.defining_polynomial
        or canonical(record["d3_certificate"]) != layout.source_bytes
    ):
        raise ValueError("general mode source or creation ring differs")
    meter = _Meter(
        max(1, min(5_000_000, budget.policy.max_work - budget.work)),
        min(60, budget.policy.max_seconds),
    )
    arithmetic = _IndependentExtension(
        precision, parent.defining_polynomial, meter,
        max_precision_bits=budget.policy.max_precision,
        max_extension_degree=12,
    )
    source = layout.source
    expected_local, expected_cross, expected_modes = [], [], []
    values = {}
    for packet_id, packet in enumerate(source["packets"]):
        budget.tick()
        occupied = packet["occupied_slots"]
        slot, edge = occupied[0]
        if slot not in values:
            polynomial = shifted_cauchy_polynomial(
                2, record["node"], 4, slot, slot, meter=meter
            )
            values[slot] = _evaluate_shifted(arithmetic, polynomial, record["zeta"])
        value = values[slot]
        row_vertex, column_vertex = source["edges"][edge]
        row_group = source["row_labels"][str(row_vertex)][0]
        column_group = source["column_labels"][str(column_vertex)][0]
        if row_group == column_group:
            if value != arithmetic.zero:
                expected_local.append([edge, edge, [list(value)]])
            continue
        expected_cross.append([edge, edge])
        # B=2, y0=y in {0,1}, so j=(y-y0)/B=0. All positive
        # geometric powers have the zero source form. At b=0 the multiplier
        # is one; its target is precisely the independently evaluated W_xx.
        if value != arithmetic.zero:
            if arithmetic.valuation(value) < 1:
                raise ValueError("independent singleton mode valuation failed")
            expected_modes.append({
                "packet": packet_id,
                "tile_residue": slot,
                "exponent": 0,
                "weight": 1,
                "source_group": column_group,
                "target_group": row_group,
                "rows": [[edge, [list(value)]]],
                "column_terms": [[edge, 1]],
            })
    budget.tick(meter.used)
    if canonical((record["local"], record["cross_pairs"], record["modes"])) != canonical(
        (expected_local, sorted(expected_cross), expected_modes)
    ):
        raise ValueError("incomplete or altered general singleton mode action")
    # A combinatorial lower-cost guard avoids a huge DP for a rejected input;
    # admitted inventories still receive a separately computed complete count.
    _complete_count(len(expected_modes), precision, budget)
    count = weighted_count((1,) * len(expected_modes), precision, budget.policy.max_tuples)
    budget.tick(max(1, len(expected_modes) * precision))
    if record["mode_tuple_count"] != count:
        raise ValueError("general weighted tuple count differs")
    return {
        "mode_completeness": "INDEPENDENT_RATIONAL_SINGLETON_ACTION",
        "mode_basis_scope": "ZERO_REDUCED_GEOMETRIC_POINT_MODES",
        "tuple_domain": "ALL_WEIGHTED_TUPLES_OVER_RETAINED_MODES",
        "weighted_tuple_count": count,
        "nonzero_cross_group_modes": len(expected_modes),
        "cross_group_pairs": len(expected_cross),
        "omitted_high_weight_terms": "DIVISIBLE_BY_2_TO_POINT_PRECISION",
        "zero_mode_elision": "ZERO_SOURCE_FORM_OR_ALL_ZERO_TARGET_COEFFICIENTS",
        "paper_formal_mode_domain_enumerated": False,
        "source_qualified": False,
    }

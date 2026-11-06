"""Singleton point-mode basis for the separate finite cycle transfer path.

This routine describes the complete weighted basis and its original tuple
cardinality, even when that cardinality exceeds the enumeration budget. It
does not enumerate or omit tuples and does not verify its own output; the
transfer certificate consumer must independently reconstruct it. The legacy
``build_general_modes`` admission and complete-stream policy are unchanged.
"""

from math import comb

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value

from .general_modes import _admit
from .model import ModeSet, Refusal, canonical


def build_transfer_basis(parent, layout, node, zeta, *, budget):
    """Build all actual singleton local terms and nonzero crossing modes.

    Modes remain in packet order and use the same point precision and payload
    schema as the existing full-tuple construction. The returned count is the
    full stars-and-bars cardinality, not the number of surviving binary
    tuples, nor an authorization to skip verification of zero coefficients.
    """
    precision, degree = _admit(parent, layout, node, zeta, budget)
    zeta = tuple(zeta)
    source = layout.source
    ring = ExtensionRing(
        precision, parent.defining_polynomial,
        max_precision_bits=budget.policy.max_precision,
    )
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
                    raise ValueError("crossing mode violates its weight-one divisibility")
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
    # Every nonzero singleton mode belongs to a distinct single-row packet;
    # hence k<=M and p_t=p+64M>k for an active call. This ensures that every
    # binary tuple lies inside the source weighted cutoff, but does not itself
    # prove that exponent >=2 has zero contribution: the independent consumer
    # must check each packet and target factor before using that conclusion.
    if len(modes) > parent.edge_count or precision <= len(modes):
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "binary support exceeds point precision")
    count = comb(precision + len(modes) - 1, len(modes))
    budget.tick(len(modes) + 1)
    if count.bit_length() > 65536:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "mode cardinality serialization cap")
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
    raw = canonical(record)
    if len(raw) > budget.policy.max_certificate_bytes:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "transfer mode basis byte cap")
    return ModeSet(layout.content_digest, raw)

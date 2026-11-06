"""Small-instance exhaustive audit of finite structural/precision pruning.

The input mode action must first pass ``verify_point_mode_action``. This file
then enumerates the finite exponent box independently with Cartesian products
(not the production DFS or R8.1 generating-function counter), applies only the
row-support pigeonhole zero rule and coefficientwise 2-adic valuation rule,
and optionally compares the exact retained sequence with an emitted stream.
If a discarded high-weight tuple lacks a checked valuation lower bound >= p,
the result is inconclusive; the checker never guesses that cancellation is
zero.
"""
from __future__ import annotations

from itertools import product


def _valuation(encoded, precision):
    values = encoded
    if isinstance(values, (tuple, list)) and len(values) == 1 and isinstance(values[0], (tuple, list)):
        values = values[0]
    if not isinstance(values, (tuple, list)) or not values:
        raise ValueError("mode coefficient coordinates are required")
    if any(type(value) is not int or not 0 <= value < (1 << precision) for value in values):
        raise ValueError("mode coefficient is not a canonical residue")
    if not any(values):
        return precision
    return min((value & -value).bit_length() - 1 if value else precision
               for value in values)


def audit_finite_pruning(modes, precision, *, emitted_tuples=None,
                         max_vectors=100_000):
    """Exhaustively audit a bounded mode tuple domain and all omitted weights.

    Structural-zero premise: one mode copy selects one target row; a mode
    cannot be selected more often than it has distinct nonzero row records,
    and a packet/target group cannot select more rows than the union of its
    mode row supports. Any tuple violating either bound is zero by the
    pigeonhole principle. These are support-level finite premises, not a
    Hall/matching certificate.

    Precision premise: every row coefficient in mode j has valuation at least
    v_j. A product with exponent vector beta therefore has valuation at least
    sum_j beta_j*v_j. Sums preserve that lower bound. A weight-pruned tuple is
    accepted only if this independently computed bound is >= precision.
    """
    try:
        if type(precision) is not int or not 1 <= precision <= 1024:
            raise ValueError("precision must be in 1..1024")
        if type(max_vectors) is not int or not 1 <= max_vectors <= 1_000_000:
            raise ValueError("max_vectors must be in 1..1000000")
        if not isinstance(modes, (tuple, list)):
            raise ValueError("mode list required")
        supports = []
        weights = []
        valuations = []
        groups = {}
        for mode in modes:
            if (not isinstance(mode, dict) or type(mode.get("packet")) is not int or
                    type(mode.get("target_group")) is not int or
                    type(mode.get("weight")) is not int or mode["weight"] < 1):
                raise ValueError("invalid mode group or weight")
            row_values = {}
            for item in mode.get("rows", ()):
                if not isinstance(item, (tuple, list)) or len(item) != 2 or type(item[0]) is not int:
                    raise ValueError("malformed mode row support")
                rid, encoded = item
                if rid in row_values:
                    raise ValueError("duplicate row support in a mode")
                row_values[rid] = _valuation(encoded, precision)
            if not row_values:
                raise ValueError("empty mode support is not a retained production mode")
            v = min(row_values.values())
            if v < mode["weight"]:
                raise ValueError("claimed mode weight exceeds independently read coefficient valuation")
            key = (mode["packet"], mode["target_group"])
            groups.setdefault(key, set()).update(row_values)
            supports.append(tuple(sorted(row_values)))
            weights.append(mode["weight"])
            valuations.append(v)
        keys = [(mode["packet"], mode["target_group"]) for mode in modes]
        group_capacity = {key: len(rows) for key, rows in groups.items()}
        caps = [len(support) for support in supports]
        candidate_bound = 1
        for cap in caps:
            candidate_bound *= cap + 1
            if candidate_bound > max_vectors:
                return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                        "reason": "finite pruning Cartesian-box cap exceeded",
                        "candidate_box_size": candidate_bound,
                        "hard_memory_limit_enforced": False}

        retained = []
        structurally_zero = 0
        precision_pruned = 0
        checked_pruned = 0
        for beta in product(*(range(cap + 1) for cap in caps)):
            group_loads = {}
            for exponent, key in zip(beta, keys):
                group_loads[key] = group_loads.get(key, 0) + exponent
            if any(load > group_capacity[key] for key, load in group_loads.items()):
                structurally_zero += 1
                continue
            total_weight = sum(exponent * weight for exponent, weight in zip(beta, weights))
            if total_weight < precision:
                retained.append(beta)
                continue
            precision_pruned += 1
            lower_bound = sum(exponent * valuation for exponent, valuation in zip(beta, valuations))
            if lower_bound < precision:
                return {"valid": False, "status": "INCONCLUSIVE_UNPROVED_PRUNING",
                        "reason": "discarded tuple lacks a coefficientwise valuation proof",
                        "tuple": beta, "weight": total_weight,
                        "valuation_lower_bound": lower_bound,
                        "precision_bits": precision,
                        "candidate_box_size": candidate_bound,
                        "hard_memory_limit_enforced": False}
            checked_pruned += 1

        if emitted_tuples is not None:
            if not isinstance(emitted_tuples, (tuple, list)):
                raise ValueError("emitted tuple stream must be a sequence")
            previous = None
            observed = []
            for beta in emitted_tuples:
                if type(beta) is not tuple or len(beta) != len(modes) or any(
                        type(v) is not int or v < 0 for v in beta):
                    raise ValueError("malformed emitted tuple")
                if previous is not None and beta <= previous:
                    raise ValueError("emitted tuple stream is duplicate or noncanonical")
                previous = beta
                observed.append(beta)
            if observed != retained:
                raise ValueError("emitted tuple stream differs from independently enumerated retained set")
        return {"valid": True, "status": "FINITE_PRUNING_AUDIT_CHECKED",
                "precision_bits": precision,
                "candidate_box_size": candidate_bound,
                "retained_tuple_count": len(retained),
                "structurally_zero_tuple_count": structurally_zero,
                "precision_pruned_tuple_count": precision_pruned,
                "valuation_certified_pruned_tuple_count": checked_pruned,
                "all_discarded_precision_terms_proved_zero_mod_2p": True,
                "support_rule": "distinct-row pigeonhole within packet/target group",
                "valuation_rule": "sum beta_j * minimum exact row-coefficient valuation",
                "hall_pruning_checked": False,
                "independent_of_production_tuple_generator": True,
                "hard_memory_limit_enforced": False,
                "universal_theorem_proven": False}
    except (ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
        return {"valid": False, "status": "INVALID_OR_INCOMPLETE_PRUNING_INPUT",
                "reason": str(exc), "hard_memory_limit_enforced": False}

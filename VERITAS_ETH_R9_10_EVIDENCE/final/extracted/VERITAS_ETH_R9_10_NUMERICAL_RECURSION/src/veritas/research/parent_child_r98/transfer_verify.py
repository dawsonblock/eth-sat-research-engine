"""Independent replay of a finite singleton cycle-transfer point certificate.

This module never imports the production child constructor, packet-entry
evaluator, Cauchy arithmetic, or transfer implementation.  It reconstructs
packet factors from actual occurrences and computes every submitted local
contraction using the independent creation-precision entry interpreter.  A
separate variable elimination checks the aggregate sum, which is also checked
against direct half-edge elimination.  This is a bounded finite checker, not a
source-qualified or universal executable refinement theorem.
"""

from itertools import product
from math import comb
from types import SimpleNamespace

from veritas.research.independent_r82.point_mode_oracle import (
    _IndependentExtension,
    _Meter,
    _evaluate_shifted,
    shifted_cauchy_polynomial,
)
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, _entry

from .independent import expected_packet_reference
from .model import (Budget, ChildGraph, ExponentTuple, ModeSet, Refusal,
                    Semantics, canonical, decode, schedule_record)
from .shrinking_layout import audit_vertex_shrinking_layout
from .shrinking_oracle import eliminate_factors, parent_point


SCHEMA = "VERITAS_R98_CYCLE_TRANSFER_POINT_V1"
FIELDS = {"schema", "parent_digest", "layout_digest", "node", "zeta",
          "precision", "modes", "groups", "result"}


def _value(raw, degree, precision):
    if (type(raw) is not list or len(raw) != 1 or type(raw[0]) is not list
            or len(raw[0]) != degree or any(type(x) is not int
                                            or not 0 <= x < (1 << precision)
                                            for x in raw[0])):
        raise ValueError("transfer value is not a canonical scalar jet")
    return (tuple(raw[0]),)


def _independent_inputs(parent, layout, node, zeta, precision, budget):
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("finite scaled parent required")
    if parent.edge_count > budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "transfer parent edge cap")
    audit_vertex_shrinking_layout(parent, layout)
    if layout.parent_digest != parent.content_digest or (layout.a, layout.u) != (1, 1):
        raise ValueError("transfer layout differs from parent or singleton parameters")
    if type(node) is not int or node not in (-1, 1):
        raise ValueError("invalid transfer Hermite node")
    if type(precision) is not int or precision != parent.precision + 64 * parent.edge_count:
        raise ValueError("altered transfer creation precision")
    if precision > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "transfer point precision cap")
    degree = parent.defining_polynomial.bit_length() - 1
    if not 2 <= degree <= 12 or type(zeta) is not list or len(zeta) != degree or any(
        type(x) is not int or not 0 <= x < 1 << precision for x in zeta
    ):
        raise ValueError("invalid transfer extension point")
    meter = _Meter(max(1, min(5_000_000, budget.policy.max_work - budget.work)),
                   min(60, budget.policy.max_seconds))
    arithmetic = _IndependentExtension(precision, parent.defining_polynomial, meter,
                                       max_precision_bits=budget.policy.max_precision,
                                       max_extension_degree=12)
    source, coefficients, modes, local, crosses, complete_modes = layout.source, {}, [], [], [], []
    for packet_id, packet in enumerate(source["packets"]):
        budget.tick()
        if len(packet["occupied_slots"]) != 1:
            raise ValueError("transfer certificate requires singleton packets")
        slot, edge = packet["occupied_slots"][0]
        if slot not in coefficients:
            polynomial = shifted_cauchy_polynomial(2, node, 4, slot, slot, meter=meter)
            coefficients[slot] = _evaluate_shifted(arithmetic, polynomial, tuple(zeta))
        row, col = source["edges"][edge]
        target = source["row_labels"][str(row)][0]
        origin = source["column_labels"][str(col)][0]
        coefficient = coefficients[slot]
        if target == origin:
            if coefficient != arithmetic.zero:
                local.append([edge, edge, [list(coefficient)]])
        else:
            crosses.append([edge, edge])
            if coefficient != arithmetic.zero:
                if arithmetic.valuation(coefficient) < 1:
                    raise ValueError("cross coefficient has insufficient two-adic valuation")
                modes.append([packet_id, edge, origin, target])
                complete_modes.append({
                    "packet": packet_id, "tile_residue": slot, "exponent": 0,
                    "weight": 1, "source_group": origin, "target_group": target,
                    "rows": [[edge, [list(coefficient)]]], "column_terms": [[edge, 1]],
                })
    budget.tick(meter.used)
    mode_record = {
        "d3_certificate": source, "node": node, "precision": precision,
        "jet_length": 1, "extension_degree": degree,
        "irreducible_polynomial": parent.defining_polynomial, "zeta": zeta,
        "local": local, "cross_pairs": sorted(crosses), "modes": complete_modes,
        "mode_tuple_count": comb(precision + len(modes) - 1, len(modes)),
    }
    return source, coefficients, modes, mode_record


def _group_contexts(parent, source, groups, budget):
    """Derive port ownership and packet occurrences from original vertices."""
    budget.tick(len(source["packets"]) + len(parent.vertices) + groups)
    packet_for_edge = {}
    for pid, packet in enumerate(source["packets"]):
        slot, edge = packet["occupied_slots"][0]
        if edge in packet_for_edge:
            raise ValueError("duplicate packet edge")
        packet_for_edge[edge] = (pid, slot)
    inherited, edges = [[] for _ in range(groups)], [[] for _ in range(groups)]
    for vertex in parent.vertices:
        labels = source["row_labels"] if vertex.side == "row" else source["column_labels"]
        group = labels.get(str(vertex.vertex_id), [0])[0]
        inherited[group].append(vertex)
        for position, edge in enumerate(vertex.ports):
            budget.tick()
            pid, slot = packet_for_edge[edge]
            edges[group].append(("Y" if vertex.side == "row" else "X", edge,
                                 pid, slot, vertex.vertex_id, position))
    return tuple((tuple(inherited[g]), tuple(sorted(edges[g], key=lambda row: (row[0] != "Y", row[1]))))
                 for g in range(groups))


def _check_child(parent, layout, source, mode_record, modes_digest, group, indices,
                 state, raw_child, context, precision, budget):
    if type(raw_child) is not str:
        raise ValueError("serialized transfer child must be an ASCII string")
    encoded = raw_child.encode("ascii")
    if len(encoded) > budget.policy.max_certificate_bytes:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "serialized transfer child cap")
    budget.tick(len(encoded) + len(source["packets"]))
    child = ChildGraph.deserialize(encoded)
    beta_values = [0] * len(mode_record["modes"])
    for i, bit in zip(indices, state):
        beta_values[i] = bit
    beta = ExponentTuple(modes_digest, tuple(beta_values))
    if (child.parent_digest != parent.content_digest or child.layout_digest != layout.content_digest
            or child.modes_digest != modes_digest or child.beta != beta
            or child.schedule_bytes != canonical(schedule_record(parent, layout))
            or child.depth != parent.depth + 1 or child.node != mode_record["node"]
            or child.zeta != tuple(mode_record["zeta"]) or child.group != group
            or child.precision != precision or child.defining_polynomial != parent.defining_polynomial):
        raise ValueError("transfer child schedule, beta or creation context differs")
    inherited, mapping = context
    if child.edge_map != mapping or child.inherited != tuple((v.side, v.vertex_id) for v in inherited):
        raise ValueError("transfer child half-edge map or inherited ordering differs")
    keys = tuple((row[0], row[1]) for row in mapping)
    if len(keys) > 4:
        raise Refusal("INCONCLUSIVE_UNSUPPORTED_TOPOLOGY", "transfer child exceeds four-edge leaf threshold")
    if source["r"] * len(keys) > 6 * parent.edge_count or len(keys) >= parent.edge_count:
        raise ValueError("transfer child violates actual strict shrinking bound")
    packet_ids = tuple(pid for pid, packet in enumerate(source["packets"])
                       if any((kind, edge) in keys for _, edge in packet["occupied_slots"]
                              for kind in ("Y", "X")))
    if child.packet_ids != packet_ids or len(child.vertices) != len(inherited) + len(packet_ids):
        raise ValueError("transfer child packet inventory differs")
    budget.tick(len(mode_record["modes"]) * len(packet_ids) + len(inherited))
    for index, (actual, old) in enumerate(zip(child.vertices, inherited)):
        kind = "Y" if old.side == "row" else "X"
        ports = tuple(keys.index((kind, edge)) for edge in old.ports)
        if (actual.side, actual.vertex_id, actual.ports, actual.tensor) != ("row", index, ports, old.tensor):
            raise ValueError("transfer inherited tensor, creation precision or ports differ")
    for index, pid in enumerate(packet_ids):
        actual = child.vertices[len(inherited) + index]
        positions, ref = expected_packet_reference(source, mode_record, group, pid,
                                                   beta.values, parent.defining_polynomial)
        ports = tuple(keys.index(key) for key in positions)
        if (actual.side, actual.vertex_id, actual.ports, actual.tensor) != ("column", index, ports, ref):
            raise ValueError("transfer packet assignment, coefficient or creation metadata differs")
    if max((len(v.ports) for v in child.vertices), default=0) > max(parent.maximum_degree, 4):
        raise ValueError("transfer child degree invariant differs")
    budget.tick(len(keys) + len(packet_ids))


def _check_mode_graph(modes, groups, precision, budget):
    if len(modes) >= precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "binary mode cutoff requires mode count below precision")
    budget.tick(groups)
    incident = [[] for _ in range(groups)]
    adjacency = [set() for _ in range(groups)]
    pairs = set()
    for index, (packet, edge, origin, target) in enumerate(modes):
        budget.tick()
        if (not 0 <= origin < groups or not 0 <= target < groups or origin == target):
            raise ValueError("invalid cross-group mode incidence")
        pair = tuple(sorted((origin, target)))
        if pair in pairs:
            raise Refusal("INCONCLUSIVE_UNSUPPORTED_TOPOLOGY", "parallel group modes are not a simple cycle")
        pairs.add(pair)
        adjacency[origin].add(target)
        adjacency[target].add(origin)
        incident[origin].append(index)
        incident[target].append(index)
    active = {g for g in range(groups) if adjacency[g]}
    if active:
        if len(active) < 3 or any(len(adjacency[g]) != 2 for g in active):
            raise Refusal("INCONCLUSIVE_UNSUPPORTED_TOPOLOGY", "cross-group modes must form one simple cycle")
        seen, todo = set(), [min(active)]
        while todo:
            budget.tick()
            node = todo.pop()
            if node not in seen:
                seen.add(node)
                todo.extend(adjacency[node] - seen)
        if seen != active or len(modes) != len(active):
            raise Refusal("INCONCLUSIVE_UNSUPPORTED_TOPOLOGY", "cross-group modes must form one connected cycle")
    return incident


def _group_value(parent, source, coefficients, modes, group, indices, state, budget, precision):
    """Sum local inherited tensors and singleton packet factors independently."""
    budget.tick(len(parent.vertices) + len(source["packets"]) + len(modes))
    ar = ReferenceArithmetic(precision, parent.defining_polynomial, 1,
                             budget.policy.max_work - budget.work,
                             max_precision_bits=budget.policy.max_precision)
    assigned = dict(zip(indices, state))
    mode_by_packet = {mode[0]: index for index, mode in enumerate(modes)}
    factors = []
    M = parent.edge_count
    for vertex in parent.vertices:
        label = source["row_labels"] if vertex.side == "row" else source["column_labels"]
        owner = label.get(str(vertex.vertex_id), [0])[0]
        if owner != group:
            continue
        ports = tuple(edge if vertex.side == "row" else M + edge for edge in vertex.ports)
        if len(ports) > budget.policy.max_factor_bits:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "transfer inherited tensor width cap")
        table = {}
        for bits in product((0, 1), repeat=len(ports)):
            budget.tick()
            table[bits] = _entry(vertex.tensor, bits, ar)
        factors.append((ports, table))
    for packet_id, packet in enumerate(source["packets"]):
        slot, edge = packet["occupied_slots"][0]
        row, col = source["edges"][edge]
        target = source["row_labels"][str(row)][0]
        origin = source["column_labels"][str(col)][0]
        if group != target and group != origin:
            continue
        w = (tuple(coefficients[slot]),)
        mode_id = mode_by_packet.get(packet_id)
        beta = assigned[mode_id] if mode_id is not None else 0
        if target == origin:
            # The local packet factor is l_Y(W X).
            factors.append(((edge, M + edge), {
                (y, x): (ar.mul(w, ar.scalar(x)) if y else
                         ar.add(ar.one, ar.neg(ar.mul(w, ar.scalar(x)))))
                for y, x in product((0, 1), repeat=2)
            }))
        elif group == target:
            # [Z^0] l_Y(W Z)=1-Y, [Z^1]=(2Y-1)W.
            factors.append(((edge,), {
                (y,): ((w if y else ar.neg(w)) if beta else ar.scalar(1 - y))
                for y in (0, 1)
            }))
        else:
            # The source linear form is X, with X^0=1 including X=0.
            factors.append(((M + edge,), {(x,): ar.scalar(x if beta else 1) for x in (0, 1)}))
        budget.tick()
    result = eliminate_factors(factors, ar, budget=budget)
    budget.tick(ar.used)
    return result


def verify_transfer_certificate(parent, layout, certificate, *, policy=None, budget=None,
                                expected_point=None):
    """Replay every group state and the complete aggregate, or refuse without a result."""
    from .shrinking_engine import DEFAULT_SHRINKING_POLICY

    if budget is None:
        budget = Budget(DEFAULT_SHRINKING_POLICY if policy is None else policy)
    elif policy is not None:
        raise TypeError("supply either policy or shared budget")
    try:
        data = decode(certificate, cap=budget.policy.max_certificate_bytes)
        if type(data) is not dict or set(data) != FIELDS or data["schema"] != SCHEMA:
            raise ValueError("transfer certificate fields or schema")
        if data["parent_digest"] != parent.content_digest or data["layout_digest"] != layout.content_digest:
            raise ValueError("transfer certificate parent or layout digest")
        node, zeta, precision = data["node"], data["zeta"], data["precision"]
        if expected_point is not None:
            if (type(expected_point) is not tuple or len(expected_point) != 3
                    or type(expected_point[0]) is not int
                    or type(expected_point[1]) is not tuple
                    or any(type(x) is not int for x in expected_point[1])
                    or type(expected_point[2]) is not int
                    or (node, tuple(zeta), precision) != expected_point):
                raise ValueError("transfer certificate differs from expected interpolation point")
        source, coefficients, modes, mode_record = _independent_inputs(
            parent, layout, node, zeta, precision, budget
        )
        if (type(data["modes"]) is not list
                or any(type(row) is not list or len(row) != 4
                       or any(type(x) is not int for x in row) for row in data["modes"])
                or data["modes"] != modes):
            raise ValueError("transfer mode inventory is altered or incomplete")
        group_count = source["r"]
        incident = _check_mode_graph(modes, group_count, precision, budget)
        modes_digest = ModeSet(layout.content_digest, canonical(mode_record)).content_digest
        contexts = _group_contexts(parent, source, group_count, budget)
        if sum(len(mapping) for _, mapping in contexts) != 2 * parent.edge_count:
            raise ValueError("transfer child incidence does not cover all half edges")
        if type(data["groups"]) is not list or len(data["groups"]) != group_count:
            raise ValueError("transfer group inventory is incomplete")
        ar = ReferenceArithmetic(precision, parent.defining_polynomial, 1,
                                 budget.policy.max_work - budget.work,
                                 max_precision_bits=budget.policy.max_precision)
        factors, checked_states = [], 0
        degree = parent.defining_polynomial.bit_length() - 1
        for group, record in enumerate(data["groups"]):
            budget.tick()
            if (type(record) is not dict or set(record) != {"group", "mode_indices", "values", "children"}
                    or type(record["group"]) is not int or record["group"] != group
                    or type(record["mode_indices"]) is not list
                    or any(type(x) is not int for x in record["mode_indices"])
                    or record["mode_indices"] != incident[group]
                    or type(record["values"]) is not list
                    or type(record["children"]) is not list
                    or len(record["values"]) != 1 << len(incident[group])
                    or len(record["children"]) != len(record["values"])):
                raise ValueError("transfer local group order, incidence or coverage differs")
            table = {}
            for bits, raw, child_raw in zip(product((0, 1), repeat=len(incident[group])),
                                            record["values"], record["children"]):
                claimed = _value(raw, degree, precision)
                _check_child(parent, layout, source, mode_record, modes_digest, group,
                             incident[group], bits, child_raw, contexts[group], precision, budget)
                actual = _group_value(parent, source, coefficients, modes, group,
                                      incident[group], bits, budget, precision)
                if actual != claimed:
                    raise ValueError("transfer local child contraction differs from independent semantics")
                table[bits] = actual
                checked_states += 1
            factors.append((tuple(incident[group]), table))
        aggregate = eliminate_factors(factors, ar, budget=budget)
        budget.tick(ar.used)
        if aggregate != _value(data["result"], degree, precision):
            raise ValueError("transfer aggregate differs from independent mode elimination")
        # This oracle evaluates the original half-edge deformation and has no
        # dependence on group children or mode contraction. It only rejects.
        point = SimpleNamespace(layout_digest=layout.content_digest,
                                certificate={"precision": precision, "node": node, "zeta": zeta})
        if aggregate != parent_point(parent, layout, point, budget=budget, max_extension_degree=12):
            raise ValueError("transfer aggregate differs from independent parent point")
        budget.tick(0)
        return {"status": "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", "result": aggregate,
                "groups": group_count, "mode_count": len(modes),
                "local_child_states_checked": checked_states,
                "support": "SINGLETON_AFFINE_DEGREE_AT_MOST_ONE_PER_MODE",
                "complete_binary_support_checked": True,
                "aggregate_check": "INDEPENDENT_BOOLEAN_MODE_ELIMINATION",
                "parent_point_check": "INDEPENDENT_HALF_EDGE_ELIMINATION",
                "creation_precision_inheritance": True, "source_qualified": False,
                "ledger": budget.report()}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {"status": getattr(exc, "status", "INVALID_CYCLE_TRANSFER_CERTIFICATE"),
                "reason": str(exc), "source_qualified": False, "ledger": budget.report()}

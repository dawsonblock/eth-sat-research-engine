"""Creation-bound row premises, without computing a network contraction.

For a constant row tensor, summing each Y bit in (1-Y)+(2Y-1)A
gives one. Only ports on nonconstant row tensors can contribute deformation
degree. The same cancellation kills mode coefficients assigned to those
constant rows, even though an individual packet entry need not vanish.
"""
from itertools import product

from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits, compile_entry, evaluate_compiled
from veritas.research.parent_child_r98.model import Refusal, canonical
from veritas.research.parent_child_r98.shrinking_oracle import _arithmetic, _entry


def _record(parent, a, active):
    return {'schema': 'VERITAS_R99_ROW_DEGREE_V1', 'parent_digest': parent.content_digest,
            'packet_exponent': a, 'nonconstant_row_ports': sorted(active),
            'degree_bound': len(active) * ((2 << a) - 1),
            'creation_precision_inheritance': True, 'source_qualified': False,
            'rule': 'CONSTANT_ROW_Y_SUM_IS_ONE'}


def certify_row_degree(parent, a, *, budget):
    if type(a) is not int or not 1 <= a <= 3:
        raise ValueError('bounded packet exponent required')
    entries = EntryBudget(EntryLimits(max_precision_bits=budget.policy.max_precision,
                                     max_seconds=min(60, budget.policy.max_seconds)))
    active = []
    for vertex in parent.vertices:
        if vertex.side != 'row':
            continue
        if len(vertex.ports) > budget.policy.max_factor_bits:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'row degree entry width cap')
        entry = compile_entry(vertex.tensor, entries)
        baseline, constant = None, True
        for bits in product((0, 1), repeat=len(vertex.ports)):
            value = evaluate_compiled(entry, bits, parent.precision, entries)
            if baseline is None:
                baseline = value
            constant = constant and value == baseline
            budget.tick()
        if not constant:
            active.extend(vertex.ports)
    budget.tick(entries.used)
    return _record(parent, a, active)


def verify_row_degree(parent, a, certificate, *, budget):
    ar = _arithmetic(parent, parent.precision, budget)
    active = []
    for vertex in parent.vertices:
        if vertex.side != 'row':
            continue
        if len(vertex.ports) > budget.policy.max_factor_bits:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'independent row degree width cap')
        values = set()
        for bits in product((0, 1), repeat=len(vertex.ports)):
            values.add(_entry(vertex.tensor, bits, ar))
            budget.tick()
        if len(values) != 1:
            active.extend(vertex.ports)
    budget.tick(ar.used)
    if canonical(certificate) != canonical(_record(parent, a, active)):
        raise ValueError('altered row constancy, degree or creation ancestry')
    return tuple(sorted(active))

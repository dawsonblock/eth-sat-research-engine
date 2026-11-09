"""Runtime checks of the hypotheses of the Lean theorem `active_node_bounds`.

`proofs_mathlib/ModeCount` proves, for one active node, the packet count
P*L <= 3M (`packet_count`), the precision bound p_t*u <= 34*M*D_t
(`precision_bound`), the per-weight mode bound (`count_weight_le`) and the
tuple count <= exp(2*pi*sqrt(34)*M/sqrt(u)) (`paper_tuple_count`). Each check
below evaluates one theorem's hypotheses and, separately, its conclusion on
the actual objects. A run conforms only when every hypothesis holds; a
conclusion that holds without its hypotheses is reported but proves nothing.
Conformance is never source qualification and never evidence of a speedup.
"""
from collections import Counter
from math import exp, log, pi, sqrt

from veritas.research.parent_child_r98.model import Refusal

TUPLE_CONSTANT = 2 * pi * sqrt(34)
PRECISION_CONSTANT = 34


def _verdict(hypotheses, conclusions, **extra):
    return {'hypotheses': hypotheses, 'conclusions': conclusions,
            'hypotheses_met': all(hypotheses.values()),
            'conclusions_met': all(conclusions.values()), **extra}


def node_precision(p, h, Dt, M, a):
    return p + 8 * h * Dt + 8 * M * (a + 1)


def packing_check(edges, row_labels, column_labels, *, k, L, H_pad):
    """`packet_count` with K of size k, so D_arr = k**2 ordered label pairs.

    Loads are X_gamma = #{(x, y) in E : (f(x), g(y)) = gamma}. The spread
    sum (X_gamma - M/D)**2 is compared after multiplying by D, in integers.
    """
    M, D = len(edges), k * k
    if type(L) is not int or L < 1 or type(H_pad) is not int or H_pad < 0:
        raise ValueError('positive packet length and padded capacity required')
    rows = Counter(x for x, _ in edges)
    cols = Counter(y for _, y in edges)
    delta = max([*rows.values(), *cols.values(), 0])
    loads = Counter((tuple(row_labels[x]), tuple(column_labels[y])) for x, y in edges)
    square = sum(n * n for n in loads.values())
    largest = max(loads.values(), default=0)
    P, remainder = divmod(H_pad * D, L)
    minimal = -(-largest // L) * D
    return _verdict(
        {'M_ge_2_D_squared_delta': M >= 2 * D * D * delta, 'M_ge_LD': M >= L * D,
         'spread_le_2M_delta': D * square - M * M <= 2 * M * delta * D,
         'L_divides_H_pad': H_pad % L == 0 and remainder == 0,
         'loads_le_H_pad': largest <= H_pad,
         'packets_times_L_le_3M': P * L <= 3 * M},
        {'minimal_packets_times_L_le_3M': minimal * L <= 3 * M},
        M=M, D=D, degree=delta, padded_packets=P, minimal_padded_packets=minimal,
        max_load=largest, scaled_spread=D * square - M * M)


def layout_packing_check(parent, layout):
    src = layout.source
    edges = [tuple(e) for e in src['edges']]
    rows = {int(x): v for x, v in src['row_labels'].items()}
    cols = {int(y): v for y, v in src['column_labels'].items()}
    return packing_check(edges, rows, cols, k=src['r'] ** layout.a, L=1 << layout.a, H_pad=src['H_pad'])


def mode_check(modes, *, P, i, L, M, Dt, packed):
    """`count_weight_le` and `mode_multiplicity` on the emitted mode tags."""
    tags = [(m['packet'], m['tile_residue'], m['exponent']) for m in modes]
    per_weight = Counter(m['weight'] for m in modes)
    cap = P * (1 << (i + 1))
    worst = max(per_weight.values(), default=0)
    return _verdict(
        {'tags_distinct': len(set(tags)) == len(tags),
         'packet_lt_P': all(0 <= m['packet'] < P for m in modes),
         'tile_lt_2_pow_i_plus_1': all(0 <= m['tile_residue'] < 1 << (i + 1) for m in modes),
         'weight_is_exponent_plus_1': all(m['weight'] == m['exponent'] + 1 for m in modes),
         'Dt_times_2_pow_i_eq_L': Dt * (1 << i) == L,
         'packets_times_L_le_3M': packed and P * L <= 3 * M},
        {'per_weight_le_P_2_pow_i_plus_1': worst <= cap,
         'per_weight_times_Dt_le_6M': worst * Dt <= 6 * M},
        largest_weight_class=worst, per_weight_cap=cap)


def precision_check(*, M, a, u, i, p, h, Dt, precision):
    """`precision_bound` with a = a' + 2u and A the least integer with p <= A*2**a'."""
    a_prev = a - 2 * u
    shape = a_prev >= 0
    A = -(-p // (1 << a_prev)) if shape else None
    hypotheses = {'a_ge_2u': shape, 'i_lt_u': 0 <= i < u, 'Dt_times_2_pow_i_eq_2_pow_a': Dt << i == 1 << a,
                  'h_times_u_le_4M': h * u <= 4 * M,
                  'A_times_u_le_M_2_pow_u': shape and A * u <= M << u,
                  'log_condition': shape and 8 * (a + 1) * u <= 1 << (a_prev + u),
                  'precision_matches_lemma': precision == node_precision(p, h, Dt, M, a)}
    return _verdict(hypotheses,
                    {'precision_times_u_le_34_M_Dt': precision * u <= PRECISION_CONSTANT * M * Dt},
                    a_previous=a_prev, A=A)


def tuple_bound_log(M, u):
    return TUPLE_CONSTANT * M / sqrt(u)


def tuple_check(*, weighted_count, support_tuples, support_weights, precision, M, u, upstream):
    """`paper_tuple_count`: compares natural logarithms, so no huge exp is formed.

    `upstream` says the packing, mode and precision hypotheses all held, which
    is what the Lean statement assumes about P, D_t and p_t.
    """
    bound = tuple_bound_log(M, u)
    in_budget = all(sum(w * b for w, b in zip(support_weights, beta)) < precision
                    for beta in support_tuples)
    return _verdict(
        {'upstream_hypotheses_met': upstream, 'u_positive': u > 0, 'precision_positive': precision > 0,
         'support_within_weight_budget': in_budget,
         'support_le_weighted_count': len(support_tuples) <= weighted_count},
        {'weighted_count_le_exp_bound': weighted_count >= 1 and log(weighted_count) <= bound},
        log_bound=f'{bound:.6f}',
        log_weighted_count=f'{log(weighted_count):.6f}' if weighted_count else None,
        bound_below_2_to_M=bound < M * log(2))


def saving_threshold():
    """Least u with exp(2*pi*sqrt(34)*M/sqrt(u)) < 2**M for every M >= 1."""
    u = int((TUPLE_CONSTANT / log(2)) ** 2)
    while TUPLE_CONSTANT / sqrt(u) >= log(2):
        u += 1
    return u


def enum_tuples(weights, budget):
    """Mirror of Lean `ModeCount.enum`: every beta with sum w_j*beta_j < budget, once."""
    if not weights:
        return [()] if budget > 0 else []
    w, rest = weights[0], weights[1:]
    return [(b,) + tail for b in range(-(-budget // w)) for tail in enum_tuples(rest, budget - w * b)]


class NodeAudit:
    """Collects per-call verdicts; `strict` refuses on the first unmet hypothesis."""

    def __init__(self, strict=False):
        self.strict, self.records = strict, []

    def add(self, call, kind, verdict, **where):
        self.records.append({'parent': call.content_digest, 'check': kind, **where, **verdict})
        if self.strict and not verdict['hypotheses_met']:
            failed = sorted(k for k, v in verdict['hypotheses'].items() if not v)
            raise Refusal('INCONCLUSIVE_THEOREM_HYPOTHESIS', f'{kind}: ' + ', '.join(failed))
        if verdict['hypotheses_met'] and not verdict['conclusions_met']:
            raise ValueError(f'{kind}: proved conclusion fails under its hypotheses')

    def report(self):
        return {'schema': 'VERITAS_R912_THEOREM_CONFORMANCE_V1', 'strict': self.strict,
                'checks': self.records,
                'conforms': bool(self.records) and all(r['hypotheses_met'] for r in self.records),
                'saving_requires_u_at_least': saving_threshold(),
                'source_qualified': False, 'theorem_mode_enabled': False,
                'evidence_for_recursion_bound': False}

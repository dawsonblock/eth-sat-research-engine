"""Finite degree-certified Taylor recovery at every prescribed Hermite node.

This is a separate algebraic optimization, not the source tapered functional.
The original q_t and p_t are recorded. A proved degree d uses d+1 distinct
residue points, then evaluates the recovered polynomial at -t/alpha with
an explicit (a+1)*d denominator loss. All nodes must recover the same value.
"""
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.extension_lagrange import distinct_residue_points, interpolate_newton
from veritas.research.paper_verification.exact_parameters import hermite_parameters
from veritas.research.parent_child_r98.model import Refusal, Semantics
from veritas.research.parent_child_r98.packing import audit_layout
from .row_degree import verify_row_degree


def degree_points(parent, layout, certificate, *, budget, max_points=256):
    audit_layout(parent, layout)
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise Refusal('INCONCLUSIVE_SOURCE_REFINEMENT', 'degree shortcut is a finite experiment')
    verify_row_degree(parent, layout.a, certificate, budget=budget)
    if type(max_points) is not int or not 1 <= max_points <= 4096:
        raise ValueError('degree point cap must be 1..4096')
    degree, e = certificate['degree_bound'], parent.defining_polynomial.bit_length() - 1
    if degree + 1 > min(max_points, 1 << e):
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'certified degree grid exceeds point or field cap')
    parameters = hermite_parameters(parent.edge_count, layout.a, layout.u, parent.precision,
                                   max_wires=budget.policy.max_edges, max_precision=budget.policy.max_precision)
    for node in parameters['nodes']:
        t, precision = node[0], node[-1]
        if precision < parent.precision + (layout.a + 1) * degree:
            raise Refusal('INCONCLUSIVE_PRECISION', 'certified Taylor denominator loss exceeds precision')
        ring = ExtensionRing(precision, parent.defining_polynomial, max_precision_bits=budget.policy.max_precision)
        for zeta in distinct_residue_points(ring, degree + 1, max_points=max_points):
            budget.tick()
            yield t, zeta, precision


def recover_degree_grid(parent, layout, certificate, rows, *, budget, max_points=256):
    expected = tuple(degree_points(parent, layout, certificate, budget=budget, max_points=max_points))
    if len(rows) != len(expected):
        raise ValueError('incomplete certified degree grid')
    degree = certificate['degree_bound']
    loss, alpha = (layout.a + 1) * degree, 2 << layout.a
    recovered, nodes = [], []
    e = parent.defining_polynomial.bit_length() - 1
    for start in range(0, len(expected), degree + 1):
        chunk, data = expected[start:start + degree + 1], rows[start:start + degree + 1]
        t, _, precision = chunk[0]
        ring = ExtensionRing(precision, parent.defining_polynomial, max_precision_bits=budget.policy.max_precision)
        for (nt, z, p), row in zip(chunk, data):
            if (type(row) not in (tuple, list) or len(row) != 4 or type(row[0]) is not int or
                row[0] != nt or tuple(row[1]) != z or any(type(x) is not int for x in row[1]) or
                type(row[2]) is not int or row[2] != p or len(row[3]) != e or
                any(type(x) is not int or not 0 <= x < ring.modulus for x in row[3])):
                raise ValueError('altered degree-grid node, residue point, precision or value')
        polynomial = interpolate_newton(ring, [z for _, z, _ in chunk],
                                        [tuple(r[3]) for r in data], max_points=max_points)
        value = []
        for coordinate in range(e):
            numerator = sum(c[coordinate] * (-t)**j * alpha**(degree-j)
                            for j, c in enumerate(polynomial)) % (1 << (parent.precision + loss))
            if numerator % (1 << loss):
                raise ValueError('nonintegral certified Taylor recovery')
            value.append(numerator >> loss)
        recovered.append(tuple(value))
        nodes.append({'node': t, 'precision': precision, 'coefficient_count': degree + 1,
                      'exact_zero_tail_from': degree + 1, 'denominator_bits': loss})
        budget.tick((degree + 1)**2 * e**2)
    if not recovered or any(value != recovered[0] for value in recovered):
        raise ValueError('complete node Taylor recoveries disagree')
    return (recovered[0],), {'method': 'DEGREE_CERTIFIED_TAYLOR_AT_EACH_SOURCE_NODE',
                            'degree_certificate': certificate, 'nodes': nodes,
                            'source_tapered_functional_used': False, 'source_qualified': False}

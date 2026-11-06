"""Restricted *original* Hermite functional, with a certified zero tail.

For a=u=1 the manuscript nodes are -1,+1 with q=3M and alpha=4.
If d bounds the deformation degree, only the first min(q,d+1) weights
can contribute. Multiplicities and input precisions remain unchanged.
This optimization does not implement the manuscript's active a_d schedule.
"""
from fractions import Fraction
from math import comb
from types import SimpleNamespace

from veritas.research.eth_interpolation.tapered_hermite import TaperedNode
from veritas.research.eth_arithmetic.residue_points import lift_binary
from veritas.research.parent_child_r98.model import Refusal, Semantics
from veritas.research.parent_child_r99.row_degree import verify_row_degree
from veritas.research.parent_child_r99.stream_recovery import StreamRecovery


def prefix_weights(q, degree, budget):
    """Exact integer cumulative binomial sums of eq:tensor-hermite-origin."""
    # S_n = sum_{k=0}^n binom(q+k-1,k) 2^(n-k).
    sums, numerator, coefficient = [], 0, 1
    for k in range(q):
        if k:
            coefficient = coefficient * (q+k-1) // k
        numerator = 2*numerator + coefficient
        sums.append(numerator)
        budget.tick()
    minus = tuple(Fraction(sums[q-1-j], 1 << (2*q-1+j))
                  for j in range(min(q, degree+1)))
    return ((-1, minus), (1, tuple((-1)**j*w for j, w in enumerate(minus))))


def reference_weights(q, degree, budget):
    """Independent rational product/reciprocal-series expansion at each node."""
    result = []
    for t in (-1, 1):
        delta = 2*t
        reciprocal = [Fraction((-1)**k * comb(q+k-1, k)) * Fraction(4, delta)**k
                      for k in range(q)]
        evaluation, factor = Fraction(-t, 4), Fraction(1, 2)**q
        # Direct summation, independent of the producer's integer cumulative sum.
        weights = []
        for j in range(min(q, degree+1)):
            weights.append(factor * sum((c*evaluation**(j+k)
                                        for k, c in enumerate(reciprocal[:q-j])), Fraction(0)))
            budget.tick(q-j)
        result.append((t, tuple(weights)))
    return tuple(result)


class Recovery(StreamRecovery):
    def __init__(self, parent, layout, certificate, *, budget, max_points=256, independent=False):
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT or (layout.a, layout.u) != (1, 1):
            raise ValueError('restricted functional requires finite a=u=1')
        verify_row_degree(parent, layout.a, certificate, budget=budget)
        d, M = certificate['degree_bound'], parent.edge_count
        if type(max_points) is not int or not 1 <= max_points <= 4096:
            raise ValueError('bounded point cap required')
        if d+1 > min(max_points, 1 << (parent.defining_polynomial.bit_length()-1)):
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'certified degree grid exceeds field/point cap')
        if not 0 <= d <= 3*M or M > budget.policy.max_edges:
            raise ValueError('invalid certified degree')
        precision, q = parent.precision+64*M, 3*M
        if precision > budget.policy.max_precision:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'Hermite precision cap')
        weights = (reference_weights if independent else prefix_weights)(q, d, budget)
        for t, row in weights:
            for w in row:
                loss = (w.denominator & -w.denominator).bit_length()-1
                if precision < parent.precision+loss:
                    raise ValueError('restricted functional precision loss')
        # Check on a basis of precisely the certified input subspace.
        for k in range(d+1):
            value = sum((w*comb(k,j)*t**(k-j)*4**j for t, row in weights
                         for j,w in enumerate(row) if j <= k), Fraction(0))
            if value != int(k == 0):
                raise ValueError('restricted Hermite monomial identity')
            budget.tick(2*(k+1))
        self.parent, self.budget, self.independent = parent, budget, independent
        self.plan = SimpleNamespace(nodes=tuple(TaperedNode(t,0,q,precision) for t in (-1,1)),
                                    target_bits=parent.precision, degree_bound=d, weights=weights)
        self.node_index = self.index = 0
        self.total = [Fraction(0)]*(parent.defining_polynomial.bit_length()-1)
        self.description = {'method': 'SOURCE_HERMITE_FUNCTIONAL_WITH_CERTIFIED_ZERO_TAIL',
            'source_degree_bound': 3*M, 'interpolated_degree_bound': d,
            'nodes': [{'t': t, 'multiplicity': q, 'precision': precision,
                       'weights': [str(w) for w in row]} for t,row in weights],
            'zero_tail_from': d+1, 'generic_point_count': 2*(3*M+1),
            'actual_point_count': 2*(d+1), 'source_qualified': False}
        self._start_node()

    def points(self):
        for node in self.plan.nodes:
            for index in range(self.plan.degree_bound+1):
                self.budget.tick()
                yield node.t, lift_binary(self.ring, index), node.precision_bits

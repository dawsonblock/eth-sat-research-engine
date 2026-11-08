"""Original node-specific Hermite functional with a certified zero tail.

For a=u=1 the manuscript nodes are -1,+1 with q=3M and alpha=4.
If d bounds the deformation degree, only the first min(q,d+1) weights
can contribute. Multiplicities and input precisions remain unchanged.
General finite a,u also use the original tapered node multiplicities and
precisions. Selecting these parameters does not implement the source schedule.
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
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT or not 1 <= layout.u <= layout.a <= 3:
            raise ValueError('bounded functional requires finite 1<=u<=a<=3')
        verify_row_degree(parent, layout.a, certificate, budget=budget)
        d, M = certificate['degree_bound'], parent.edge_count
        if type(max_points) is not int or not 1 <= max_points <= 4096:
            raise ValueError('bounded point cap required')
        if d+1 > min(max_points, 1 << (parent.defining_polynomial.bit_length()-1)):
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'certified degree grid exceeds field/point cap')
        source_degree=M*((2 << layout.a)-1)
        if not 0 <= d <= source_degree or M > budget.policy.max_edges:
            raise ValueError('invalid certified degree')
        from veritas.research.paper_verification.exact_parameters import hermite_parameters
        pars=hermite_parameters(M,layout.a,layout.u,parent.precision,
            max_wires=budget.policy.max_edges,max_precision=budget.policy.max_precision)
        nodes=tuple(TaperedNode(t,i,q,p) for t,i,q,_,p in pars['nodes'])
        alpha=pars['alpha']
        if max(n.precision_bits for n in nodes)>budget.policy.max_precision:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT','Hermite precision cap')
        if (layout.a,layout.u)==(1,1):
            weights=(reference_weights if independent else prefix_weights)(3*M,d,budget)
        elif independent:
            from veritas.research.parent_child_r912.tapered_weights import reference_prefix
            weights=reference_prefix(nodes,alpha,d,budget)
        else:
            from veritas.research.eth_interpolation.source_hermite import _functional
            budget.tick(sum(n.multiplicity**2 for n in nodes)*len(nodes))
            weights=_functional(nodes,alpha,d)
        precisions={n.t:n.precision_bits for n in nodes}
        for t, row in weights:
            for w in row:
                loss = (w.denominator & -w.denominator).bit_length()-1
                if precisions[t] < parent.precision+loss:
                    raise ValueError('restricted functional precision loss')
        # Check on a basis of precisely the certified input subspace.
        for k in range(d+1):
            value = sum((w*comb(k,j)*t**(k-j)*alpha**j for t, row in weights
                         for j,w in enumerate(row) if j <= k), Fraction(0))
            if value != int(k == 0):
                raise ValueError('restricted Hermite monomial identity')
            budget.tick(2*(k+1))
        self.parent, self.budget, self.independent = parent, budget, independent
        self.plan = SimpleNamespace(nodes=nodes,
                                    target_bits=parent.precision, degree_bound=d, weights=weights)
        self.node_index = self.index = 0
        self.total = [Fraction(0)]*(parent.defining_polynomial.bit_length()-1)
        self.description = {'method': 'SOURCE_HERMITE_FUNCTIONAL_WITH_CERTIFIED_ZERO_TAIL',
            'source_degree_bound': source_degree, 'interpolated_degree_bound': d,
            'nodes': [{'t': n.t, 'multiplicity': n.multiplicity, 'precision': n.precision_bits,
                       'weights': [str(w) for w in row]} for n,(_,row) in zip(nodes,weights)],
            'zero_tail_from': d+1, 'generic_point_count': len(nodes)*(source_degree+1),
            'actual_point_count': len(nodes)*(d+1), 'source_qualified': False}
        self._start_node()

    def points(self):
        for node in self.plan.nodes:
            for index in range(self.plan.degree_bound+1):
                self.budget.tick()
                yield node.t, lift_binary(self.ring, index), node.precision_bits

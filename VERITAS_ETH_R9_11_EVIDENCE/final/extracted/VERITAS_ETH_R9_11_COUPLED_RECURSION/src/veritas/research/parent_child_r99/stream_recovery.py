"""Online Newton interpolation and coefficientwise exact tapered functional.

One node polynomial and Newton basis are live at a time; point values and
completed jets are not retained. Rational plan weights remain bounded data.
"""
from fractions import Fraction

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.residue_points import lift_binary
from veritas.research.eth_interpolation.extension_lagrange import evaluate_polynomial
from .recovery import make_packet_plan


class StreamRecovery:
    def __init__(self, parent, layout, *, budget, max_points=256, independent=False):
        self.parent, self.budget = parent, budget
        self.plan = make_packet_plan(parent, layout, budget=budget, max_points=max_points, streaming=True)
        self.node_index = self.index = 0
        self.total = [Fraction(0) for _ in range(parent.defining_polynomial.bit_length()-1)]
        self.independent = independent
        self._start_node()

    def _start_node(self):
        if self.node_index >= len(self.plan.nodes):
            return
        self.node = self.plan.nodes[self.node_index]
        self.ring = ExtensionRing(self.node.precision_bits, self.parent.defining_polynomial,
                                 max_precision_bits=self.budget.policy.max_precision)
        # The consumer uses separate extension arithmetic, not production mul/inverse.
        if self.independent:
            from veritas.research.independent_r82.point_mode_oracle import _IndependentExtension, meter_from_budget
            self.meter = meter_from_budget(self.budget,
                'Hermite interpolation: depth='+str(self.parent.depth)+', node='+str(self.node.t))
            self.ar = _IndependentExtension(self.node.precision_bits, self.parent.defining_polynomial,
                self.meter, max_precision_bits=self.budget.policy.max_precision, max_extension_degree=12)
        else:
            self.ar = self.ring
        self.polynomial, self.basis = [], [self.ar.one]
        self.index = 0
        self.diagonal, self.abscissae = [], []

    def add(self, t, point, precision, value):
        if self.node_index >= len(self.plan.nodes):
            raise ValueError('excess interpolation point')
        ar, node = self.ar, self.node
        expected = lift_binary(self.ring, self.index)
        if (type(t) is not int or t != node.t or type(precision) is not int or
            precision != node.precision_bits or tuple(point) != expected or
            any(type(x) is not int for x in point) or len(value) != self.ring.e or
            any(type(x) is not int or not 0 <= x < self.ring.modulus for x in value)):
            raise ValueError('streamed point order, residue or precision mismatch')
        point, value = tuple(point), tuple(value)
        if self.independent:
            # Independent divided-difference recurrence, not the producer's
            # residual divided by the evaluated Newton basis.
            diagonal = [value]
            for k, old in enumerate(self.diagonal):
                denominator = ar.sub(point, self.abscissae[-1-k])
                diagonal.append(ar.mul(ar.sub(diagonal[-1], old), ar.inverse(denominator)))
            self.diagonal = diagonal
            self.abscissae.append(point)
            coefficient = diagonal[-1]
        else:
            residual = ar.sub(value, evaluate_polynomial(ar, self.polynomial, point))
            denominator = evaluate_polynomial(ar, self.basis, point)
            coefficient = ar.mul(residual, ar.inverse(denominator))
        self.polynomial.append(ar.zero)
        self.polynomial = [ar.add(c, ar.mul(coefficient, b)) for c, b in zip(self.polynomial, self.basis)]
        updated = [ar.zero] * (len(self.basis) + 1)
        for i, b in enumerate(self.basis):
            updated[i] = ar.sub(updated[i], ar.mul(point, b))
            updated[i+1] = ar.add(updated[i+1], b)
        self.basis = updated
        self.index += 1
        self.budget.tick(8 * self.index * self.ring.e**2)
        if self.index != self.plan.degree_bound + 1:
            return
        _, weights = self.plan.weights[self.node_index]
        for coefficient, weight in zip(self.polynomial, weights):
            # Check each coefficient's available precision against denominator loss.
            den = weight.denominator
            loss = (den & -den).bit_length() - 1
            if node.precision_bits < self.plan.target_bits + loss:
                raise ValueError('insufficient coefficientwise Hermite precision')
            for j, c in enumerate(coefficient):
                self.total[j] += weight * c
        if self.independent:
            self.budget.tick(self.meter.used)
        self.polynomial, self.basis = [], []
        self.diagonal, self.abscissae = [], []
        self.node_index += 1
        self._start_node()

    def finish(self):
        if self.node_index != len(self.plan.nodes):
            raise ValueError('incomplete streamed Hermite grid')
        modulus = 1 << self.plan.target_bits
        result = []
        for value in self.total:
            if value.denominator % 2 == 0:
                raise ValueError('nonintegral streamed Hermite recovery')
            result.append(value.numerator * pow(value.denominator, -1, modulus) % modulus)
        return (tuple(result),)

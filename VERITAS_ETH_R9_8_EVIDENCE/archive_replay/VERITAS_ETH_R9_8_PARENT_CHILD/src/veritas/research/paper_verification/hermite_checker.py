"""Finite, exact test of the recovery functional and its per-coefficient precision."""

from fractions import Fraction
from math import comb
from .exact_parameters import hermite_parameters


def check_functional(plan):
    q = hermite_parameters(plan.wires, plan.packets_exponent, plan.u, plan.target_bits)
    expected = [(t, i, k, prec) for t, i, k, _, prec in q["nodes"]]
    actual = [(n.t, n.valuation, n.multiplicity, n.precision_bits) for n in plan.nodes]
    if actual != expected or (plan.alpha, plan.degree_bound) != (
        q["alpha"],
        q["degree_bound"],
    ):
        raise ValueError("Hermite schedule differs")
    if len(plan.weights) != len(expected):
        raise ValueError("incomplete functional")
    worst_loss = 0
    for (t, _, k, prec), (other, weights) in zip(expected, plan.weights):
        if t != other or len(weights) != min(k, plan.degree_bound + 1):
            raise ValueError("coefficient inventory")
        for w in weights:
            if type(w) not in (int, Fraction):
                raise ValueError("inexact weight")
            den = Fraction(w).denominator
            loss = (den & -den).bit_length() - 1
            worst_loss = max(worst_loss, loss)
            if loss > prec - plan.target_bits:
                raise ValueError("under-precision coefficient")
    if type(plan.guard_bits) is not int or plan.guard_bits != worst_loss:
        raise ValueError("incorrect recovery guard bits")
    for d in range(plan.degree_bound + 1):
        value = sum(
            w * comb(d, j) * t ** (d - j) * plan.alpha**j
            for t, ws in plan.weights
            for j, w in enumerate(ws)
            if j <= d
        )
        if value != int(d == 0):
            raise ValueError("monomial basis failure")
    return q


def recover_reference(plan, jets, precisions):
    check_functional(plan)
    if set(jets) != {n.t for n in plan.nodes} or set(jets) != set(precisions):
        raise ValueError("node set differs")
    value = Fraction(0)
    for node, (_, weights) in zip(plan.nodes, plan.weights):
        entries, ps = jets[node.t], precisions[node.t]
        if len(entries) != len(weights) or len(ps) != len(weights):
            raise ValueError("coefficient count differs")
        for w, v, bits in zip(weights, entries, ps):
            if (
                type(bits) is not int
                or bits != node.precision_bits
                or type(v) is not int
                or not 0 <= v < 1 << bits
            ):
                raise ValueError("invalid input precision or residue")
            value += w * v
    if value.denominator % 2 == 0:
        raise ValueError("recovery requires a nonunit inverse")
    mod = 1 << plan.target_bits
    return value.numerator * pow(value.denominator, -1, mod) % mod

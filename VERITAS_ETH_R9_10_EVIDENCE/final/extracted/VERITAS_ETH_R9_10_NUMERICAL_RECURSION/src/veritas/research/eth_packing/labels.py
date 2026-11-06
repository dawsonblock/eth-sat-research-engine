"""Conditional-expectation derandomization for endpoint symbol LOAD balancing.

This is a limited *local load* potential, NOT a proof of the manuscript's
full collision-packing lemma. The packet constructor measures the remaining
class-collision/packet bounds separately, and fails closed if requested.
"""
from __future__ import annotations
from fractions import Fraction


def assign_endpoint_labels(edges, *, r: int, a: int):
    edges = tuple((int(u), int(v)) for u, v in edges)
    if not edges:
        return {}
    vertices = sorted(set(u for u, _ in edges) | set(v for _, v in edges))
    weights = {v: [0, 0] for v in vertices}
    for u, v in edges:
        weights[u][0] += 1
        weights[v][1] += 1
    m = len(edges)
    labels = {v: [] for v in vertices}
    for coordinate in range(a):
        assigned = {v: None for v in vertices}
        current = [[0] * r for _ in range(2)]
        remaining = [sum(weights[v][side] for v in vertices) for side in range(2)]
        remain_squares = [sum(weights[v][side] ** 2 for v in vertices) for side in range(2)]
        target = Fraction(m, r)
        # Exact expectation of sum of squared deviations of port loads.
        for v in sorted(vertices, key=lambda x: (-sum(weights[x]), x)):
            best = None
            for candidate in range(r):
                potential = Fraction(0)
                for side in range(2):
                    w = weights[v][side]
                    mu_rem = Fraction(remaining[side] - w, r)
                    variance = Fraction((remain_squares[side] - w*w) * (r-1), r*r)
                    for sym in range(r):
                        mu = current[side][sym] + (w if sym == candidate else 0) + mu_rem
                        potential += (mu - target)**2 + variance
                trial = (potential, candidate)
                if best is None or trial < best:
                    best = trial
            chosen = best[1]
            assigned[v] = chosen
            labels[v].append(chosen)
            for side in range(2):
                w = weights[v][side]
                remaining[side] -= w
                remain_squares[side] -= w*w
                current[side][chosen] += w
    return {v: tuple(label) for v, label in labels.items()}

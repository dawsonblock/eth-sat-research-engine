"""Occurrence-chain CNF network, with a deliberately exhaustive evaluator."""
from dataclasses import dataclass

from eth_sat.model import CNF


@dataclass(frozen=True)
class OccurrenceNetwork:
    formula: CNF
    # Each tuple holds (occurrence number, positive polarity).
    clauses: tuple
    equality_edges: tuple
    unused_variables: int
    occurrences: int


def encode_cnf(formula: CNF) -> OccurrenceNetwork:
    last = {}
    clauses, edges = [], []
    count = 0
    for clause in formula.clauses:
        encoded = []
        for literal in clause:
            encoded.append((count, not literal.negated))
            if literal.variable in last:
                edges.append((last[literal.variable], count))
            last[literal.variable] = count
            count += 1
        clauses.append(tuple(encoded))
    return OccurrenceNetwork(formula, tuple(clauses), tuple(edges),
                             formula.num_variables - len(last), count)


def count_occurrences(network: OccurrenceNetwork, max_assignments=1_000_000):
    """Evaluate clause and equality tensors; includes unused-variable factor."""
    if (1 << network.occurrences) > max_assignments:
        raise ValueError("occurrence enumeration exceeds max_assignments")
    total = 0
    for bits in range(1 << network.occurrences):
        if any(((bits >> a) & 1) != ((bits >> b) & 1) for a, b in network.equality_edges):
            continue
        if all(any(bool((bits >> position) & 1) == positive for position, positive in clause)
               for clause in network.clauses):
            total += 1
    return total << network.unused_variables

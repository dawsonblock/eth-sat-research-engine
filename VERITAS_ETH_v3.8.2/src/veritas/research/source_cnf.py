"""The pinned paper's fixed-density CNF-to-bipartite-network construction.

Clause normalization, equality trees, and edge subdivision preserve each
assignment of occurring variables. Unused variables are accounted for outside
the network, as in ``subsec:sharp-fixed-density``. This is a finite reference,
not the arbitrary-density reduction or a complexity qualification.
"""
from __future__ import annotations
from dataclasses import dataclass

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.bounded_degree import bounded_degree_from_cnf


@dataclass(frozen=True)
class SourceCNFNetwork:
    network: TensorNetwork
    normalized_cnf: CNF
    unused_variables: tuple[int, ...]
    dropped_tautologies: tuple[int, ...]
    original_edges: int
    formula_digest: str


def source_cnf_network(cnf: CNF, *, max_clause_width=8, max_wires=64,
                       max_factors=10000) -> SourceCNFNetwork:
    """Construct the source's equality-tree and subdivided bipartite graph.

    A clause contains at most one port for each distinct variable. A tautology
    is removed; an empty clause is a zero scalar. Each original edge becomes
    two wires joined by a binary equality vertex. The equality-chain gadget is
    a particular trivalent equality tree, with d-2 internal vertices for d>=3.
    Caps apply to the resulting graph. No partial graph is returned on failure.
    """
    if not isinstance(cnf, CNF):
        raise TypeError('CNF required')
    if type(max_wires) is not int or not 0 <= max_wires <= 400000:
        raise ValueError('max_wires must be in 0..400000')
    if type(max_factors) is not int or not 0 <= max_factors <= 400000:
        raise ValueError('max_factors must be in 0..400000')
    if type(max_clause_width) is not int or not 0 <= max_clause_width <= 12:
        raise ValueError('max_clause_width must be in 0..12')
    normalized = []
    dropped = []
    used = set()
    for index, clause in enumerate(cnf.clauses):
        seen = set()
        distinct = []
        tautology = False
        for literal in clause:
            if -literal in seen:
                tautology = True
                break
            if literal not in seen:
                seen.add(literal)
                distinct.append(literal)
        if tautology:
            dropped.append(index)
            continue
        if len(distinct) > max_clause_width:
            raise ValueError('normalized clause width exceeds cap')
        normalized.append(tuple(distinct))
        used.update(abs(x) for x in distinct)
    normalized_cnf = CNF(cnf.n, tuple(normalized))
    # Existing COPY3 chain is a tree of trivalent equality tensors. Its free
    # scalar factors are excluded, since the paper restores them after counting.
    old, _ = bounded_degree_from_cnf(normalized_cnf, max_clause_width=max_clause_width,
                                     max_wires=max_wires // 2,
                                     max_factors=min(400000, max_factors + cnf.n))
    old_factors = tuple(f for f in old.factors if not f.label.endswith(':free'))
    if len(old_factors) + old.edges > max_factors:
        raise ValueError('subdivided factors exceed network budget')
    incidence = [0] * old.edges
    result = []
    for factor in old_factors:
        ports = []
        for edge in factor.ports:
            endpoint = incidence[edge]
            if endpoint >= 2:
                raise ArithmeticError('invalid source graph incidence')
            ports.append(2 * edge + endpoint)
            incidence[edge] += 1
        result.append(Factor(tuple(ports), factor.table, 'row:' + factor.label))
    if any(count != 2 for count in incidence):
        raise ArithmeticError('invalid source graph incidence')
    for edge in range(old.edges):
        result.append(Factor((2 * edge, 2 * edge + 1), (1, 0, 0, 1),
                             f'col:subdivision:{edge}'))
    network = TensorNetwork(2 * old.edges, tuple(result))
    return SourceCNFNetwork(network, normalized_cnf,
                            tuple(v for v in range(1, cnf.n + 1) if v not in used),
                            tuple(dropped), old.edges, cnf.digest())

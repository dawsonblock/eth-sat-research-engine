"""Independent structural checker for the fixed-density CNF encoding.

Checks the equality trees and edge-subdivision graph from the original CNF,
without calling the encoder. This is a finite graph check, not a formal proof.
"""
from collections import Counter, defaultdict
from veritas.core.cnf import CNF
from veritas.research.source_cnf import SourceCNFNetwork
from veritas.research.tensor import TensorNetwork


def check_source_cnf_network(cnf, encoded, *, max_wires=100_000, max_factors=100_000):
    if not isinstance(cnf, CNF) or not isinstance(encoded, SourceCNFNetwork):
        raise TypeError('CNF and SourceCNFNetwork required')
    if type(max_wires) is not int or not 0 <= max_wires <= 400_000:
        raise ValueError('invalid verification wire cap')
    if type(max_factors) is not int or not 0 <= max_factors <= 400_000:
        raise ValueError('invalid verification factor cap')
    network = encoded.network
    if not isinstance(network, TensorNetwork):
        return {'valid': False, 'status': 'INVALID_SOURCE_CNF_NETWORK',
                'reason': 'tensor network required'}
    if network.edges > max_wires or len(network.factors) > max_factors:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
    try:
        _check(cnf, encoded)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return {'valid': False, 'status': 'INVALID_SOURCE_CNF_NETWORK', 'reason': str(exc)}
    return {'valid': True, 'status': 'FINITE_SOURCE_CNF_STRUCTURE_CHECKED',
            'general_theorem_proven': False}


def _check(cnf, encoded):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    require(encoded.formula_digest == cnf.digest(), 'formula digest mismatch')
    clauses, dropped, used = [], [], set()
    for i, clause in enumerate(cnf.clauses):
        literal_set = set(clause)
        if any(-lit in literal_set for lit in clause):
            dropped.append(i)
        else:
            deduplicated = tuple(dict.fromkeys(clause))
            clauses.append(deduplicated)
            used.update(abs(lit) for lit in deduplicated)
    unused = tuple(v for v in range(1, cnf.n + 1) if v not in used)
    require(encoded.normalized_cnf == CNF(cnf.n, tuple(clauses)) and
            encoded.dropped_tautologies == tuple(dropped) and
            encoded.unused_variables == unused, 'normalization mismatch')
    network = encoded.network
    require(type(encoded.original_edges) is int and encoded.original_edges >= 0,
            'invalid original edge count')
    require(network.edges == 2 * encoded.original_edges, 'subdivision edge count mismatch')
    rows = [f for f in network.factors if f.label.startswith('row:')]
    columns = [f for f in network.factors if f.label.startswith('col:')]
    require(len(rows) + len(columns) == len(network.factors), 'invalid bipartite side')
    require(len(columns) == encoded.original_edges, 'missing subdivision vertices')
    require(len({f.label for f in network.factors}) == len(network.factors), 'duplicate labels')
    owners = {}
    for factor in rows:
        for position, edge in enumerate(factor.ports):
            require(edge not in owners, 'wire has multiple row endpoints')
            owners[edge] = (factor, position)
    require(set(owners) == set(range(network.edges)), 'wire lacks row endpoint')
    clause_factors = {f.label: f for f in rows if f.label.startswith('row:clause:')}
    require(set(clause_factors) == {f'row:clause:{i}' for i in range(len(clauses))},
            'clause vertices mismatch')
    for i, clause in enumerate(clauses):
        factor = clause_factors[f'row:clause:{i}']
        expected = tuple(int(any(bool(mask & (1 << j)) == (lit > 0)
                                 for j, lit in enumerate(clause)))
                         for mask in range(1 << len(clause)))
        require(len(factor.ports) == len(clause) and factor.table == expected,
                'clause tensor mismatch')
    variable_factors = defaultdict(set)
    for factor in rows:
        if factor.label.startswith('row:clause:'):
            continue
        parts = factor.label.split(':')
        require(len(parts) in (4, 5) and parts[:2] == ['row', 'variable'] and
                parts[3] == 'copy', 'unexpected row factor')
        var = int(parts[2])
        require(var in used and 1 <= len(factor.ports) <= 3, 'invalid equality vertex')
        table_size = 1 << len(factor.ports)
        require(factor.table == tuple(int(i in (0, table_size-1)) for i in range(table_size)),
                'equality tensor mismatch')
        variable_factors[var].add(factor)
    terminals = Counter()
    neighbors = defaultdict(lambda: defaultdict(set))
    internal_edges = Counter()
    for col in columns:
        require(len(col.ports) == 2 and col.table == (1, 0, 0, 1), 'invalid subdivision tensor')
        left, right = (owners[p] for p in col.ports)
        a, b = left[0], right[0]
        ac = a.label.startswith('row:clause:')
        bc = b.label.startswith('row:clause:')
        require(not (ac and bc) and a != b, 'invalid pre-subdivision edge')
        if ac or bc:
            clause, pos = left if ac else right
            eq = b if ac else a
            ci = int(clause.label.rsplit(':', 1)[1])
            var = abs(clauses[ci][pos])
            require(eq in variable_factors[var], 'clause port attached to wrong variable')
            terminals[var] += 1
        else:
            va, vb = int(a.label.split(':')[2]), int(b.label.split(':')[2])
            require(va == vb and a in variable_factors[va] and b in variable_factors[va],
                    'equality tree joins different variables')
            require(b.label not in neighbors[va][a.label], 'parallel equality tree edge')
            neighbors[va][a.label].add(b.label)
            neighbors[va][b.label].add(a.label)
            internal_edges[va] += 1
    occurrences = Counter(abs(lit) for clause in clauses for lit in clause)
    for var in used:
        d = occurrences[var]
        factors = variable_factors[var]
        require(terminals[var] == d, 'missing equality tree terminal')
        require(len(factors) == (1 if d <= 2 else d-2), 'wrong equality tree size')
        require(all(len(f.ports) == (d if d <= 2 else 3) for f in factors),
                'wrong equality tree degree')
        require(internal_edges[var] == max(0, len(factors)-1), 'wrong equality tree edge count')
        seen = set()
        stack = [next(iter(factors)).label]
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(neighbors[var][node] - seen)
        require(len(seen) == len(factors), 'equality tree disconnected')

"""Parsimonious Boolean CNF -> constant-degree integer tensor network.

A variable of d occurrences is replaced with a chain of ternary COPY
(equality) tensors connected by d-3 auxiliary wires. Every assignment to
the original CNF's variables has **exactly one** consistent extension to
internal gadget wires. Isolated original variables still contribute a scalar
factor 2. Thus the contraction equals the original #SAT count exactly.

This is a correct local degree-reduction construction; it is NOT the
counting-preserving sparsification lemma or the special low-rank ETH
contraction, and does not establish a subexponential running time.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork


@dataclass(frozen=True)
class BoundedDegreeStats:
    n_variables: int
    n_clauses: int
    original_occurrence_wires: int
    auxiliary_wires: int
    resulting_wires: int
    resulting_factors: int
    maximum_variable_occurrences: int
    maximum_factor_degree: int
    equality_factors: int
    isolated_variables: int
    method: str = 'EXACT_COPY3_EQUALITY_CHAIN'
    proof_status: str = 'STRUCTURAL_BIJECTION_NOT_FORMALIZED_IN_LEAN'


def _copy(ports: tuple[int, ...], label: str) -> Factor:
    """All incident bits equal; arbitrary degree <=3 (including unary)."""
    if not 1 <= len(ports) <= 3:
        raise AssertionError('COPY factor must have 1..3 incident wires')
    size = 1 << len(ports)
    return Factor(ports, tuple(int(i in (0, size-1)) for i in range(size)), label)


def bounded_degree_from_cnf(cnf: CNF, *, max_clause_width: int = 8,
                            max_wires: int = 50_000,
                            max_factors: int = 50_000) -> tuple[TensorNetwork, BoundedDegreeStats]:
    """Create count-preserving factor network, with explicit resource caps.

    Clause tensors require O(2^k) space for width k. Variable COPY tensors
    are always arity <= 3; the overall maximum degree is max(k,3).
    Exactly two factor ports touch every wire, including newly added wires.
    """
    if type(max_clause_width) is not int or not 0 <= max_clause_width <= 12:
        raise ValueError('max_clause_width must be an integer in 0..12')
    if type(max_wires) is not int or not 0 <= max_wires <= 400_000:
        raise ValueError('max_wires must be an integer in 0..400000')
    if type(max_factors) is not int or not 0 <= max_factors <= 400_000:
        raise ValueError('max_factors must be an integer in 0..400000')
    occurrences: list[list[int]] = [[] for _ in range(cnf.n+1)]
    factors: list[Factor] = []
    next_wire = 0
    for cid, clause in enumerate(cnf.clauses):
        if len(clause) > max_clause_width:
            raise ValueError('clause width exceeds requested bounded-degree cap')
        if len(factors) >= max_factors or next_wire + len(clause) > max_wires:
            raise ValueError('clause tensor exceeds network resource caps')
        ports = tuple(range(next_wire, next_wire+len(clause)))
        for lit, wire in zip(clause, ports):
            occurrences[abs(lit)].append(wire)
        next_wire += len(clause)
        table = tuple(int(any(bool(mask & (1 << j)) == (lit > 0)
                               for j, lit in enumerate(clause)))
                      for mask in range(1 << len(clause)))
        factors.append(Factor(ports, table, f'clause:{cid}'))
    original_wires = next_wire
    equality_factors = isolated = max_occ = 0
    for var in range(1, cnf.n+1):
        ports = tuple(occurrences[var])
        d = len(ports)
        max_occ = max(max_occ, d)
        if d == 0:
            isolated += 1
            planned: list[Factor] = [Factor((), (2,), f'variable:{var}:free')]
            additional = 0
        elif d <= 3:
            planned = [_copy(ports, f'variable:{var}:copy')]
            additional = 0
        else:
            additional = d-3
            if next_wire + additional > max_wires:
                raise ValueError('auxiliary equality wires exceed network budget')
            aux = tuple(range(next_wire, next_wire+additional))
            planned = [_copy((ports[0],ports[1],aux[0]), f'variable:{var}:copy:0')]
            for j in range(1, d-3):
                planned.append(_copy((aux[j-1],ports[j+1],aux[j]),
                                     f'variable:{var}:copy:{j}'))
            planned.append(_copy((aux[-1],ports[-2],ports[-1]),
                                 f'variable:{var}:copy:{d-3}'))
        if len(factors)+len(planned) > max_factors:
            raise ValueError('variable gadget exceeds network factor budget')
        factors.extend(planned)
        equality_factors += sum(bool(f.ports) for f in planned)
        next_wire += additional
    network = TensorNetwork(next_wire, tuple(factors))
    degree = max((len(f.ports) for f in factors), default=0)
    if degree > max(max_clause_width,3):
        raise AssertionError('bounded degree invariant violated')
    stats = BoundedDegreeStats(cnf.n,len(cnf.clauses),original_wires,
                               next_wire-original_wires,next_wire,len(factors),
                               max_occ,degree,equality_factors,isolated)
    return network, stats


def describe_network(cnf: CNF, *, max_clause_width: int = 8,
                     max_wires: int = 50_000,
                     max_factors: int = 50_000) -> dict:
    net, stats = bounded_degree_from_cnf(cnf, max_clause_width=max_clause_width,
                                         max_wires=max_wires, max_factors=max_factors)
    return {**asdict(stats), 'formula_sha256':cnf.digest(),
            'count_preservation':'MATHEMATICAL_BIJECTION',
            'solver_status':'STRUCTURAL_CONSTRUCTION_ONLY',
            'warning':'No subexponential speedup or manuscript D.4.4 certification is claimed.'}

"""Exact violation-count generating polynomial via a tensor network.

For CNF F with m (possibly empty) clauses:
    H_F(T) = sum_{x in {0,1}^n} T^{number_of_violated_clauses(x)}.
The constant coefficient is #SAT(F), H_F(1) == 2**n.  Each original
clause factor is changed from 0/1 to T/1. Equality and isolated-variable
factors are retained. Generic polynomial-semiring bucket elimination yields
all coefficients, or their exact residues in Z/(2**p)[T]/(T**(m+1)).

This is an elementary, EXPONENTIAL worst-case reference implementation.
It does NOT implement the OpenAI paper's Cauchy deformation, mode
construction, or subexponential recursive contraction.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import comb
import time

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf


@dataclass
class PolynomialStats:
    table_entries_evaluated: int = 0
    multiplication_pairs: int = 0
    v2_zero_pairs_elided: int = 0
    max_intermediate_arity: int = 0


def evaluate_polynomial(coefficients: list[int] | tuple[int, ...], x: int,
                        precision_bits: int | None = None) -> int:
    if type(x) is not int:
        raise ValueError("evaluation point must be an integer")
    if precision_bits is not None and (type(precision_bits) is not int or not 1 <= precision_bits <= 64):
        raise ValueError("precision_bits must be 1..64")
    total = 0
    modulus = (1 << precision_bits) if precision_bits is not None else None
    for a in reversed(coefficients):
        total = (total*x + a) % modulus if modulus is not None else total*x+a
    return total


def recover_zero_from_positive_nodes(values: list[int] | tuple[int, ...],
                                     precision_bits: int | None = None) -> int:
    """Exact interpolation at zero for f of degree < len(values).

    From f(1), ..., f(d+1), finite differences imply
      f(0) = sum_{j=1}^{d+1} (-1)^(j-1) C(d+1,j) f(j).
    All coefficients are integers, so this also holds modulo 2**p.
    Not an ETH speedup: computing the nonzero evaluations remains expensive.
    """
    if not values or len(values) > 25 or any(type(v) is not int for v in values):
        raise ValueError("one to 25 integer evaluations required")
    if precision_bits is not None and (type(precision_bits) is not int or not 1 <= precision_bits <= 64):
        raise ValueError("precision_bits must be 1..64")
    size = len(values)
    result = sum((1 if j%2 else -1)*comb(size,j)*val for j,val in enumerate(values, 1))
    return result % (1 << precision_bits) if precision_bits is not None else result


def multiply_polynomials(a: tuple[int, ...], b: tuple[int, ...], *,
                         precision_bits: int | None = None,
                         stats: PolynomialStats | None = None) -> tuple[int, ...]:
    if len(a) != len(b) or not a:
        raise ValueError("polynomial size mismatch")
    if precision_bits is not None and (type(precision_bits) is not int or not 1 <= precision_bits <= 64):
        raise ValueError("precision_bits must be 1..64")
    modulus = 1 << precision_bits if precision_bits is not None else None
    result = [0]*len(a)
    for i, x in enumerate(a):
        if not x: continue
        for j, y in enumerate(b[:len(a)-i]):
            if not y: continue
            if stats is not None: stats.multiplication_pairs += 1
            z = x*y
            if modulus is not None:
                if z % modulus == 0:
                    if stats is not None: stats.v2_zero_pairs_elided += 1
                    continue   # EXACT in Z/(2**p), not a numerical heuristic
                result[i+j] = (result[i+j] + z) % modulus
            else:
                result[i+j] += z
    return tuple(result)


def exact_violation_histogram(cnf: CNF, *, max_vars: int = 18) -> list[int]:
    """Independent bit-assignment oracle; n <= 18."""
    if cnf.n > max_vars:
        raise ValueError("histogram oracle exceeds variable cap")
    hist = [0]*(len(cnf.clauses)+1)
    for mask in range(1 << cnf.n):
        violations = 0
        for clause in cnf.clauses:
            if not any((bool(mask & (1 << (abs(lit)-1))) == (lit > 0)) for lit in clause):
                violations += 1
        hist[violations] += 1
    return hist


def eliminate_violation_polynomial(
    cnf: CNF, *, precision_bits: int | None = None,
    max_table_entries: int = 1 << 14,
    max_edges: int = 24,
    max_clauses: int = 12,
    timeout_s: float = 10.0,
) -> tuple[list[int], PolynomialStats]:
    """Compute exact coefficients or exact modulo-2**p coefficient residues.

    No floating-point interpolation and no unverified dropped term.
    Worst case remains exponential in elimination width and input degree.
    """
    if precision_bits is not None and (type(precision_bits) is not int or not 1 <= precision_bits <= 64):
        raise ValueError("precision_bits must be 1..64")
    if not 1 <= max_table_entries <= 1 << 18 or not 0 <= max_edges <= 30 or not 0 <= max_clauses <= 24:
        raise ValueError("invalid research limits")
    if not 0 < timeout_s <= 30:
        raise ValueError("invalid timeout")
    if len(cnf.clauses) > max_clauses or sum(len(c) for c in cnf.clauses) > max_edges:
        raise ValueError("research clause/edge budget exceeded")
    network = from_cnf(cnf, max_degree=14)
    size = len(cnf.clauses)+1
    one = (1,) + (0,)*(size-1)
    t = (0,1) + (0,)*(size-2) if size>1 else one
    modulus = (1 << precision_bits) if precision_bits is not None else None
    stats = PolynomialStats()
    # factor is [ports, table] in which each entry is an entire coefficient tuple
    factors: list[tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]] = []
    for fact in network.factors:
        if fact.label.startswith("clause:"):
            table = tuple(one if entry else t for entry in fact.table)
        else:
            table = tuple((entry if modulus is None else entry % modulus,)+(0,)*(size-1)
                          for entry in fact.table)
        factors.append((fact.ports, table))
    deadline = time.monotonic() + timeout_s

    def value(ports, table, assignment):
        idx = sum(1 << i for i, port in enumerate(ports) if assignment[port])
        return table[idx]

    for edge in range(network.edges):
        if time.monotonic() > deadline:
            raise TimeoutError("polynomial tensor contraction time exceeded")
        chosen = [(ports, table) for ports, table in factors if edge in ports]
        factors = [(ports, table) for ports, table in factors if edge not in ports]
        neighbors = tuple(sorted(set().union(*(set(ports) for ports, _ in chosen)) - {edge}))
        if (1 << len(neighbors)) > max_table_entries:
            raise ValueError("intermediate polynomial tensor exceeds table cap")
        stats.max_intermediate_arity = max(stats.max_intermediate_arity, len(neighbors))
        table_new = []
        for mask in range(1 << len(neighbors)):
            stats.table_entries_evaluated += 1
            if stats.table_entries_evaluated % 256 == 0 and time.monotonic() > deadline:
                raise TimeoutError("polynomial tensor contraction time exceeded")
            assignment = {p: bool(mask >> i & 1) for i,p in enumerate(neighbors)}
            sums = [0]*size
            for edge_val in (False,True):
                assignment[edge] = edge_val
                accumulated = one
                for ports, table in chosen:
                    accumulated = multiply_polynomials(accumulated, value(ports,table,assignment),
                                                         precision_bits=precision_bits, stats=stats)
                    if not any(accumulated): break
                for j,v in enumerate(accumulated):
                    sums[j] += v
                    if modulus is not None: sums[j] %= modulus
            table_new.append(tuple(sums))
        factors.append((neighbors, tuple(table_new)))
    answer = one
    for ports, table in factors:
        if ports:
            raise AssertionError("uneliminated polynomial port")
        answer = multiply_polynomials(answer, table[0], precision_bits=precision_bits, stats=stats)
    return list(answer), stats

"""Boolean factor networks and exact contraction baselines.

These methods are exhaustive edge enumeration and generic bucket elimination.
They DO NOT implement the paper's Cauchy deformation, two-adic mode
truncation, or subexponential recursive contraction theorem.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import time
from veritas.core.cnf import CNF


@dataclass(frozen=True)
class Factor:
    ports: tuple[int, ...]
    table: tuple[int, ...]
    label: str

    def __post_init__(self):
        object.__setattr__(self, 'ports', tuple(self.ports))
        object.__setattr__(self, 'table', tuple(self.table))
        if not isinstance(self.label, str):
            raise ValueError("factor label must be a string")
        if any(type(port) is not int or port < 0 for port in self.ports):
            raise ValueError("ports must be nonnegative integers")
        if len(self.table) != 1 << len(self.ports):
            raise ValueError("table must contain 2^degree entries")
        if len(set(self.ports)) != len(self.ports):
            raise ValueError("duplicate port in factor")
        if any(type(v) is not int for v in self.table):
            raise ValueError("tensor entries must be integers")

    def value(self, edge_values: dict[int, bool]) -> int:
        idx = sum(1 << i for i, p in enumerate(self.ports) if edge_values[p])
        return self.table[idx]


@dataclass(frozen=True)
class TensorNetwork:
    edges: int
    factors: tuple[Factor, ...]

    def __post_init__(self):
        if type(self.edges) is not int or self.edges < 0:
            raise ValueError("edges must be a nonnegative integer")
        object.__setattr__(self, 'factors', tuple(self.factors))
        if any(not isinstance(factor, Factor) for factor in self.factors):
            raise ValueError("factors must be Factor objects")
        counts = [0]*self.edges
        for factor in self.factors:
            for port in factor.ports:
                if not 0 <= port < self.edges:
                    raise ValueError("port out of bounds")
                counts[port] += 1
        if any(count != 2 for count in counts):
            raise ValueError("every edge must connect exactly two ports")


def from_cnf(cnf: CNF, *, max_degree: int = 15) -> TensorNetwork:
    occurrences: dict[int, list[int]] = {i: [] for i in range(1, cnf.n+1)}
    edge = 0
    factors = []
    for cidx, clause in enumerate(cnf.clauses):
        ports = []
        for lit in clause:
            ports.append(edge)
            occurrences[abs(lit)].append(edge)
            edge += 1
        if len(ports) > max_degree:
            raise ValueError("clause has too many literal occurrences for dense table")
        table = []
        for mask in range(1 << len(ports)):
            table.append(int(any(bool(mask & (1 << j)) == (lit > 0) for j, lit in enumerate(clause))))
        factors.append(Factor(tuple(ports), tuple(table), f"clause:{cidx}"))
    for var, ports in occurrences.items():
        if len(ports) > max_degree:
            raise ValueError("variable has too many occurrences for dense equality tensor")
        # An isolated Boolean variable contributes two choices.
        table = tuple(2 if len(ports) == 0 else int(mask in (0, (1 << len(ports))-1))
                      for mask in range(1 << len(ports)))
        factors.append(Factor(tuple(ports), table, f"variable:{var}"))
    return TensorNetwork(edge, tuple(factors))


def brute_contract(network: TensorNetwork, *, max_edges: int = 19, modulus: int | None = None, timeout_s: float = 30.0) -> int:
    if network.edges > max_edges:
        raise ValueError(f"edge enumeration exceeds {max_edges} edges")
    total = 0
    deadline = time.monotonic() + timeout_s
    for mask in range(1 << network.edges):
        if mask % 1024 == 0 and time.monotonic() > deadline:
            raise TimeoutError("tensor edge enumeration exceeded time budget")
        values = {i: bool(mask & (1 << i)) for i in range(network.edges)}
        prod = 1
        for factor in network.factors:
            prod *= factor.value(values)
            if not prod: break
        total += prod
        if modulus is not None: total %= modulus
    return total


def eliminate(network: TensorNetwork, *, max_table_entries: int = 1 << 18,
              modulus: int | None = None, timeout_s: float = 30.0,
              _start_bucket=None, _finish_bucket=None) -> int:
    """Exact generic bucket elimination over wire variables (not ETH algorithm)."""
    if max_table_entries < 1: raise ValueError("invalid table cap")
    deadline = time.monotonic() + timeout_s
    factors = list(network.factors)
    for edge in range(network.edges):
        if time.monotonic() > deadline:
            raise TimeoutError("tensor elimination exceeded time budget")
        selected = [f for f in factors if edge in f.ports]
        factors = [f for f in factors if edge not in f.ports]
        neighbors = sorted(set().union(*(set(f.ports) for f in selected)) - {edge})
        if 1 << len(neighbors) > max_table_entries:
            raise ValueError("intermediate tensor table exceeds budget")
        if _start_bucket is not None:
            _start_bucket(len(selected), 1 << len(neighbors))
        outputs = []
        for counter, bits in enumerate(product((False, True), repeat=len(neighbors))):
            if counter % 1024 == 0 and time.monotonic() > deadline:
                raise TimeoutError("tensor elimination exceeded time budget")
            assignment = dict(zip(neighbors, bits))
            result = 0
            for val in (False, True):
                assignment[edge] = val
                p = 1
                for f in selected:
                    p *= f.value(assignment)
                result += p
            outputs.append(result % modulus if modulus else result)
        # itertools.product's bit ordering puts the last bit in the low-order
        # position; Factors require the FIRST port to be the low-order bit.
        table = [0]*len(outputs)
        for i, bits in enumerate(product((False, True), repeat=len(neighbors))):
            index = sum(1 << j for j, bit in enumerate(bits) if bit)
            table[index] = outputs[i]
        output = Factor(tuple(neighbors), tuple(table), f"eliminate:{edge}")
        if _finish_bucket is not None:
            _finish_bucket(edge, output)
        factors.append(output)
    result = 1
    for f in factors:
        if f.ports: raise AssertionError("uneliminated port")
        result *= f.table[0]
    return result % modulus if modulus else result

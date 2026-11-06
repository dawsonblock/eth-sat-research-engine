"""Certificates for deterministic sum-product elimination on explicit integer factors."""

from math import prod
from time import monotonic

from veritas.research.tensor import eliminate
from .boundary import _digest, _require


def _row(edge, ports, values):
    return {
        "edge": edge,
        "free_ports": tuple(ports),
        "table_entries": len(values),
        "table_sha256": _digest(values),
    }


def verify_steps(network, precision, steps, result, run):
    """Independent little-endian gather. Consume each occurrence by its factor ID."""
    modulus = 1 << precision
    current = [(f.ports, f.table) for f in network.factors]
    _require(len(steps) == network.edges, "incomplete elimination steps")
    for edge, claimed in enumerate(steps):
        bucket = [item for item in current if edge in item[0]]
        current = [item for item in current if edge not in item[0]]
        neighbors = sorted({p for ports, _ in bucket for p in ports if p != edge})
        n = len(neighbors)
        rows = 1 << n
        run.charge("elimination_checker_factor_visits", rows * (1 + 2 * len(bucket)))
        # Encoding the eliminated bit above all free bits makes the two arms independent.
        position = {wire: i for i, wire in enumerate(neighbors + [edge])}
        maps = [tuple(position[wire] for wire in ports) for ports, _ in bucket]
        values = []
        for mask in range(rows):
            if mask % 512 == 0:
                run.charge("elimination_deadline_checks")
            subtotal = 0
            for address in (mask, mask + rows):
                term = 1
                for mapping, (_, table) in zip(maps, bucket):
                    index = sum(
                        ((address >> slot) & 1) << i for i, slot in enumerate(mapping)
                    )
                    entry = table[index]
                    run.counts["reference_multiply_operand_bit_products"] += (
                        term.bit_length() * entry.bit_length()
                    )
                    term = term * entry % modulus
                subtotal += term
            values.append(subtotal % modulus)
        _require(
            _digest(claimed) == _digest(_row(edge, neighbors, values)),
            "elimination table differs",
        )
        current.append((tuple(neighbors), values))
    _require(all(not ports for ports, _ in current), "uncontracted elimination ports")
    _require(
        result == prod(table[0] for _, table in current) % modulus,
        "elimination residue differs",
    )


def certified_elimination(network, precision, run):
    steps = []
    result = eliminate(
        network,
        modulus=1 << precision,
        max_table_entries=1 << 16,
        timeout_s=max(0, run.policy.max_seconds - (monotonic() - run.start)),
        _start_bucket=lambda count, rows: run.charge(
            "elimination_factor_visits", rows * (1 + 2 * count)
        ),
        _finish_bucket=lambda edge, factor: steps.append(
            _row(edge, factor.ports, factor.table)
        ),
    )
    verify_steps(network, precision, steps, result, run)
    return result, steps

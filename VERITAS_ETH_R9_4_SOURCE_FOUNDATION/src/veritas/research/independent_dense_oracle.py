"""Independent bounded oracle for one scalar L=2 Cauchy evaluation.

This is a 2**M table algorithm, not the recursive contraction theorem.
It is independent of the packet-matrix and weighted-mode implementations.
"""
from __future__ import annotations

from .dense_cauchy_testbed import DenseWorkLimit


def diagonal_node_four_oracle(a, b, wires, *, max_table_entries=1 << 16,
                              max_scalar_ops=10_000_000):
    """Return the original count and F(4) modulo 4 for two Boolean tables.

    At T=4 the L=2 Cauchy matrix is [[-45,-60],[-36,-45]], hence is
    diagonal with entries 3 modulo 4. For one coordinate the corresponding
    half-edge matrix has columns (1,0) and (2,3). A direct in-place
    Kronecker butterfly contracts these matrices against the first table.
    Input tables are supplied by the caller; the oracle allocates one table
    of 2**wires entries after its table and operation preflight.
    """
    if type(wires) is not int or not 1 <= wires <= 16:
        raise ValueError('wires must be in 1..16')
    if (type(max_table_entries) is not int or max_table_entries < 1 or
            type(max_scalar_ops) is not int or max_scalar_ops < 1):
        raise ValueError('positive table and scalar-operation caps required')
    size = 1 << wires
    if size > max_table_entries:
        raise DenseWorkLimit('independent oracle table-entry cap exceeded')
    # Per butterfly: two multiplications and one addition. The two dot
    # products each charge one multiplication and one addition per entry.
    ops = 3 * wires * (size // 2) + 4 * size
    if ops > max_scalar_ops:
        raise DenseWorkLimit('independent oracle scalar-operation cap exceeded')
    if len(a) != size or len(b) != size:
        raise ValueError('both Boolean tables must contain 2**wires entries')
    if any(type(v) is not int or v not in (0, 1) for table in (a, b) for v in table):
        raise ValueError('Boolean table entries must be integer zero or one')
    original = sum(x * y for x, y in zip(a, b))
    values = list(a)
    for bit in range(wires):
        stride = 1 << bit
        for block in range(0, size, 2 * stride):
            for offset in range(stride):
                lo = block + offset
                zero, one = values[lo], values[lo + stride]
                values[lo + stride] = (2 * zero + 3 * one) % 4
    deformed = sum(x * y for x, y in zip(values, b)) % 4
    return {'original_exact': original, 'deformed_mod_4': deformed,
            'scalar_ops_upper_count': ops, 'allocated_table_entries': size,
            'modulus_bits': 2, 'independent_of_mode_generator': True,
            'subexponential_bound_proven': False}

"""Finite scalar Cauchy experiment; NOT manuscript D.4.4 recursion.

Two arbitrary dense Boolean tensor tables share M wires. The L=2 Cauchy
kernel is evaluated at T=4, expanded as equality + 2*perturbation per row,
and terms of weight >= precision are discarded modulo 2**precision.
Full local packet matrices are applied exactly. A separate half-edge brute
force oracle is deliberately capped and normally completes only for M<=8.
"""
from dataclasses import dataclass
from itertools import combinations
from math import comb, prod


class DenseWorkLimit(RuntimeError):
    pass


@dataclass
class ScalarWork:
    max_ops: int
    additions: int = 0
    multiplications: int = 0

    def charge(self, additions=0, multiplications=0):
        if self.additions + self.multiplications + additions + multiplications > self.max_ops:
            raise DenseWorkLimit('counted scalar-operation budget exceeded')
        self.additions += additions
        self.multiplications += multiplications


def _kernel(t):
    # Independent direct product definition, not the package's Cauchy routines.
    roots = (-2, -1, 0, 1)
    derivative = prod(-r for r in roots if r != 0)
    return tuple(tuple(prod(t-r for r in roots if r != y-x) // derivative
                       for y in range(2)) for x in range(2))


def _packet_matrix(kernel, selected, modulus):
    out = []
    for y in range(4):
        row = []
        for x in range(4):
            values = []
            for i in range(2):
                yi, xi = (y >> i) & 1, (x >> i) & 1
                h = sum(kernel[i][j] * ((x >> j) & 1) for j in range(2))
                h = h if yi else 1-h
                delta = int(yi == xi)
                difference = h-delta
                if difference % 2:
                    raise ArithmeticError('chosen kernel is not equality modulo 2')
                values.append((difference // 2) if selected >> i & 1 else delta)
            row.append(values[0] * values[1] % modulus)
        out.append(tuple(row))
    return tuple(out)


def _full_packet_matrix(kernel, modulus):
    out = []
    for y in range(4):
        row = []
        for x in range(4):
            factor = 1
            for i in range(2):
                s = sum(kernel[i][j] * ((x >> j) & 1) for j in range(2))
                factor *= s if (y >> i) & 1 else 1-s
            row.append(factor % modulus)
        out.append(tuple(row))
    return tuple(out)


def _transform(values, matrices, modulus, work):
    """Contract product of 4x4 packet matrices against a full dense table."""
    current = list(values)
    size = len(current)
    for packet, matrix in enumerate(matrices):
        step = 1 << (2*packet)
        other = [0] * size
        # Charge the exact scalar multiplications and additions in this stage.
        work.charge(additions=3*size, multiplications=4*size)
        for base in range(0, size, 4*step):
            for offset in range(step):
                idx = base+offset
                a,b,c,d = (current[idx+j*step] for j in range(4))
                for x in range(4):
                    other[idx+x*step] = (a*matrix[0][x] + b*matrix[1][x] +
                                         c*matrix[2][x] + d*matrix[3][x]) % modulus
        current = other
    return current


def _dot(a, b, modulus, work):
    work.charge(additions=len(a), multiplications=len(a))
    return sum(x*y for x,y in zip(a,b)) % modulus


def direct_halfedges(a, b, wires, modulus, *, max_pairs=1 << 16):
    """Independent scalar half-edge enumeration, no matrix or mode expansion."""
    size = 1 << wires
    if size*size > max_pairs:
        raise DenseWorkLimit('direct half-edge pair cap exceeded')
    kernel = _kernel(4)
    total = 0
    for x in range(size):
        for y in range(size):
            value = a[y] * b[x]
            for row in range(wires):
                pair = row // 2
                i = row % 2
                s = sum(kernel[i][j] * ((x >> (2*pair+j)) & 1) for j in range(2))
                value *= s if (y >> row) & 1 else 1-s
            total = (total + value) % modulus
    return total


def experiment(a, b, wires, precision=2, *, max_ops=120_000_000, max_direct_pairs=1 << 16):
    """Return exact finite residues and partial, explicitly scoped operation counts."""
    if type(wires) is not int or not 8 <= wires <= 16 or wires % 2:
        raise ValueError('wires must be even and in 8..16')
    if type(precision) is not int or not 1 <= precision <= 3:
        raise ValueError('precision must be 1..3')
    if type(max_ops) is not int or max_ops < 1 or type(max_direct_pairs) is not int or max_direct_pairs < 0:
        raise ValueError('invalid resource cap')
    size = 1 << wires
    if len(a) != size or len(b) != size or any(type(x) is not int for x in (*a, *b)):
        raise ValueError('both dense tables must contain 2**wires integer entries')
    modulus = 1 << precision
    mode_count = sum(comb(wires, j) for j in range(min(precision, wires+1)))
    # Fail before any dense transformation; cost excludes table and kernel creation.
    per_transform_ops = 7 * size * (wires//2) + 2*size
    estimate = (1+mode_count)*per_transform_ops + 2*size + 2*mode_count
    if estimate > max_ops:
        raise DenseWorkLimit(f'counted transform operation estimate {estimate} exceeds cap')
    work = ScalarWork(max_ops)
    original = _dot(a, b, modulus, work)
    original_work = {'additions':work.additions, 'multiplications':work.multiplications}
    kernel = _kernel(4)
    full_matrix = _full_packet_matrix(kernel, modulus)
    deformed = _dot(_transform(a, (full_matrix,)*(wires//2), modulus, work), b, modulus, work)
    deformed_work = {'additions':work.additions-original_work['additions'],
                     'multiplications':work.multiplications-original_work['multiplications']}
    modes_start = (work.additions, work.multiplications)
    modes = []
    accumulated = 0
    for degree in range(precision):
        for subset in combinations(range(wires), degree):
            selected = set(subset)
            matrices = tuple(_packet_matrix(kernel,
                             int(2*i in selected) + 2*int(2*i+1 in selected), modulus)
                             for i in range(wires//2))
            coefficient = _dot(_transform(a, matrices, modulus, work), b, modulus, work)
            contribution = ((1 << degree)*coefficient) % modulus
            work.charge(additions=1, multiplications=1)
            accumulated = (accumulated+contribution) % modulus
            modes.append({'wires':list(subset), 'weight':degree,
                          'coefficient_modulus':coefficient, 'contribution':contribution})
    if accumulated != deformed:
        raise ArithmeticError('weighted mode reconstruction differs from packet transform')
    try:
        brute = direct_halfedges(a, b, wires, modulus, max_pairs=max_direct_pairs)
    except DenseWorkLimit:
        brute = None
    if brute is not None and brute != deformed:
        raise ArithmeticError('independent half-edge oracle differs')
    return {'wires':wires, 'precision':precision, 'modulus':modulus,
            'original_count_modulus':original, 'deformed_value_modulus':deformed,
            'retained_structural_modes':len(modes),
            'nonzero_mode_contributions':sum(m['contribution'] != 0 for m in modes),
            'discarded_structural_modes':(1 << wires)-len(modes),
            'modes':modes, 'largest_child_wires':wires,
            'child_interpretation':'each retained term retains both original full-scope dense tensors',
            'direct_halfedge_value':brute,
            'direct_halfedge_status':'checked' if brute is not None else 'BLOCKED_PAIR_CAP',
            'counted_scalar_additions':work.additions,
            'counted_scalar_multiplications':work.multiplications,
            'counted_work_by_phase':{'original':original_work, 'full_deformed':deformed_work,
                                     'all_modes':{'additions':work.additions-modes_start[0],
                                                  'multiplications':work.multiplications-modes_start[1]}},
            'count_scope':'dot products and packet transforms only; excludes mode/kernel construction and bit costs',
            'peak_dense_working_tables':4,
            'complexity_or_theorem_proven':False}

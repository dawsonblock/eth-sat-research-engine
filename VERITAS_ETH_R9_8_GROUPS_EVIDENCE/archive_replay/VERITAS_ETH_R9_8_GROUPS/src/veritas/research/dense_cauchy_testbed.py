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

from veritas.research.eth_interpolation.shifted_cauchy import shifted_fraction_coefficients
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials
from veritas.research.hermite_ring import hermite_plan, modular_fraction, reconstruct_mod


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
    rows = []
    for x in range(2):
        row = []
        for y in range(2):
            numerator = prod(t-r for r in roots if r != y-x)
            if numerator % derivative:
                raise ArithmeticError('integer Cauchy kernel division was not exact')
            row.append(numerator // derivative)
        rows.append(tuple(row))
    return tuple(rows)


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


def direct_halfedges(a, b, wires, modulus, *, node=4, max_pairs=1 << 16):
    """Independent scalar half-edge enumeration, no matrix or mode expansion."""
    size = 1 << wires
    if size*size > max_pairs:
        raise DenseWorkLimit('direct half-edge pair cap exceeded')
    kernel = _kernel(node)
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


def _row_factor_jet(kernel_jets, row, y_bit, x_pair, modulus):
    """One affine Boolean row factor, as coefficients in the local z variable."""
    order = len(kernel_jets[0][0])
    value = [0] * order
    for column in range(2):
        if (x_pair >> column) & 1:
            for degree, coefficient in enumerate(kernel_jets[row][column]):
                value[degree] = (value[degree] + coefficient) % modulus
    if y_bit:
        return tuple(value)
    value[0] = (1 - value[0]) % modulus
    return (value[0],) + tuple((-coefficient) % modulus for coefficient in value[1:])


def _packet_jet_matrix(node, order, modulus, *, alpha=4):
    """Build exact L=2 packet entries in (Z/2^P)[z]/(z**order)."""
    polynomials = cauchy_matrix_polynomials(2)
    kernel_jets = []
    for row in range(2):
        kernel_row = []
        for column in range(2):
            shifted = shifted_fraction_coefficients(polynomials[row][column], node, alpha)
            if len(shifted) > 4:
                raise ArithmeticError('L=2 Cauchy entry exceeded its cubic degree')
            coefficients = tuple(modular_fraction(value, modulus.bit_length() - 1)
                                 for value in shifted)
            kernel_row.append(coefficients + (0,) * (4 - len(coefficients)))
        kernel_jets.append(tuple(kernel_row))
    packet = []
    for y in range(4):
        packet_row = []
        factors_by_row = [
            tuple(_row_factor_jet(kernel_jets, row, (y >> row) & 1, x_pair, modulus)
                  for x_pair in range(4))
            for row in range(2)
        ]
        for x in range(4):
            x_pair = x
            factors = [factors_by_row[row][x_pair] for row in range(2)]
            value = [0] * min(order, 7)
            for i, left in enumerate(factors[0]):
                for j, right in enumerate(factors[1]):
                    if i + j < len(value):
                        value[i + j] = (value[i + j] + left * right) % modulus
            packet_row.append(tuple(value) + (0,) * (order - len(value)))
        packet.append(tuple(packet_row))
    return tuple(packet)


def _jet_operation_estimate(packet, wires, order, table_size):
    support = sum(order - degree
                  for row in packet for entry in row
                  for degree, coefficient in enumerate(entry[:min(order, 7)])
                  if coefficient and degree < order)
    # Each local 4x4 matrix is applied to table_size/4 disjoint blocks per packet.
    transform_terms = support * (table_size // 4) * (wires // 2)
    final_dot_terms = table_size * order
    # Each executed term uses one multiply and one accumulation. Include the
    # reference dot product once; construction and rational-plan work are
    # accounted separately in the returned scope text.
    reference_terms = table_size
    return 2 * (transform_terms + final_dot_terms + reference_terms)


def _contract_jet_at_node(a, b, wires, node, *, order, modulus, packet, work):
    size = 1 << wires
    zero = (0,) * order
    current = [((value % modulus),) + zero[1:] for value in a]
    supports = tuple(tuple(tuple((degree, coefficient)
                                 for degree, coefficient in enumerate(entry[:min(order, 7)])
                                 if coefficient and degree < order)
                         for entry in row) for row in packet)
    for packet_index in range(wires // 2):
        step = 1 << (2 * packet_index)
        other = [zero] * size
        for base in range(0, size, 4 * step):
            for offset in range(step):
                start = base + offset
                sources = tuple(current[start + y * step] for y in range(4))
                for x in range(4):
                    accum = [0] * order
                    for y in range(4):
                        for degree, coefficient in supports[y][x]:
                            # Charge the complete nonzero batch before doing
                            # its arithmetic, preserving fail-closed limits.
                            work.charge(additions=order - degree,
                                        multiplications=order - degree)
                            for source_degree in range(order - degree):
                                accum[source_degree + degree] += (
                                    sources[y][source_degree] * coefficient)
                    other[start + x * step] = tuple(value % modulus for value in accum)
        current = other
    result = [0] * order
    for index, weight in enumerate(b):
        work.charge(additions=order, multiplications=order)
        for degree, coefficient in enumerate(current[index]):
            result[degree] += coefficient * weight
    return tuple(value % modulus for value in result)


def reconstruct_zero(
    a,
    b,
    wires,
    precision=2,
    *,
    max_scalar_ops=40_000_000,
    max_live_jet_entries=2_000_000,
):
    """Recover the original contraction from nonzero L=2 Cauchy-node jets.

    The L=2 kernel entries have degree 3. There is one affine row factor per
    wire, so the full contraction polynomial has degree at most 3*wires.
    Three nonzero roots (-2,-1,1), with confluent jets, determine F(0). This
    is a finite Hermite identity check, not the manuscript's tapered Lemma
    D.5 schedule. Work caps reject before the dense transforms begin.
    """
    if type(wires) is not int or not 8 <= wires <= 16 or wires % 2:
        raise ValueError('wires must be even and in 8..16')
    if type(precision) is not int or not 1 <= precision <= 17:
        raise ValueError('reconstruction precision must be 1..17')
    if (type(max_scalar_ops) is not int or max_scalar_ops < 1 or
            type(max_live_jet_entries) is not int or max_live_jet_entries < 1):
        raise ValueError('invalid Hermite work or storage cap')
    size = 1 << wires
    if len(a) != size or len(b) != size or any(type(x) is not int for x in (*a, *b)):
        raise ValueError('both dense tables must contain 2**wires integer entries')

    degree_bound = 3 * wires
    total_samples = degree_bound + 1
    quotient, remainder = divmod(total_samples, 3)
    multiplicities = tuple(quotient + (index < remainder) for index in range(3))
    nodes = tuple(zip((-2, -1, 1), multiplicities))
    plan = hermite_plan(nodes, alpha=4, degree_bound=degree_bound)
    data_bits = precision + plan.guard_bits
    if data_bits > 256:
        raise DenseWorkLimit('Hermite guard precision exceeds the ring cap')
    # A node with multiplicity q only contributes coefficients 0..q-1 to
    # the Hermite functional. Polynomial multiplication modulo z**q
    # preserves those coefficients, so computing all 3*M+1 at every node
    # is unnecessary.
    live_entries = 2 * size * max(multiplicities)
    if live_entries > max_live_jet_entries:
        raise DenseWorkLimit(
            f'live jet-entry estimate {live_entries} exceeds cap {max_live_jet_entries}')

    modulus = 1 << data_bits
    packets = tuple(_packet_jet_matrix(node, multiplicity, modulus)
                    for node, multiplicity in nodes)
    estimated_ops = sum(_jet_operation_estimate(packet, wires, multiplicity, size)
                        for (_, multiplicity), packet in zip(nodes, packets))
    if estimated_ops > max_scalar_ops:
        raise DenseWorkLimit(
            f'nonzero-node Hermite transform estimate {estimated_ops} exceeds cap {max_scalar_ops}')

    work = ScalarWork(max_scalar_ops)
    node_jets = tuple(_contract_jet_at_node(
        a, b, wires, node, order=multiplicity, modulus=modulus,
        packet=packet, work=work)
        for (node, multiplicity), packet in zip(nodes, packets))
    independent_jet_checks = []
    if size * size <= (1 << 16):
        for (node, multiplicity), jet in zip(nodes, node_jets):
            # The omitted tail has integral coefficients. Evaluating at a
            # multiple of 2**ceil(data_bits/q) makes every omitted term
            # divisible by 2**data_bits, so direct evaluation remains valid.
            z_guard = 1 << ((data_bits + multiplicity - 1) // multiplicity)
            for z in (0, z_guard):
                deformed_node = node + 4 * z
                jet_value = sum(coefficient * pow(z, degree)
                                for degree, coefficient in enumerate(jet)) % modulus
                direct_value = direct_halfedges(
                    a, b, wires, modulus, node=deformed_node, max_pairs=1 << 16)
                if jet_value != direct_value:
                    raise ArithmeticError('packet jet differs from independent half-edge evaluation')
                independent_jet_checks.append({
                    'interpolation_node': node,
                    'local_coordinate': z,
                    'deformed_parameter': deformed_node,
                    'jet_value': jet_value,
                    'direct_halfedge_value': direct_value,
                })
    recovered = reconstruct_mod(plan, node_jets, precision_bits=precision,
                                data_precision_bits=data_bits)
    work.charge(additions=size, multiplications=size)
    direct_exact = sum(x * y for x, y in zip(a, b))
    direct = direct_exact % (1 << precision)
    if recovered != direct:
        raise ArithmeticError('nonzero-node Hermite reconstruction differs from original contraction')
    return {
        'status': 'EXACT_HERMITE_RECONSTRUCTION_CHECKED',
        'wires': wires,
        'degree_bound': degree_bound,
        'nodes_and_multiplicities': [{'node': node, 'multiplicity': multiplicity}
                                     for node, multiplicity in nodes],
        'computed_jet_orders': list(multiplicities),
        'scale_alpha': 4,
        'target_precision_bits': precision,
        'guard_bits': plan.guard_bits,
        'input_jet_precision_bits': data_bits,
        'reconstructed_at_zero_modulus': 1 << precision,
        'reconstructed_at_zero': recovered,
        'independent_original_contraction': direct,
        'counted_scalar_operations': work.additions + work.multiplications,
        'counted_additions': work.additions,
        'counted_multiplications': work.multiplications,
        'estimated_scalar_operations': estimated_ops,
        'peak_live_jet_entries_estimate': live_entries,
        'independent_jet_evaluation_checks': independent_jet_checks,
        'independent_jet_evaluation_status': ('checked' if independent_jet_checks
                                              else 'BLOCKED_PAIR_CAP'),
        'work_scope': ('packet-jet tensor transforms and original reference dot product; '
                       'excludes input validation, matrix construction, exact rational '
                       'Hermite planning, modular reduction costs and bit complexity'),
        'manuscript_tapered_recurrence_implemented': False,
        'subexponential_bound_proven': False,
    }

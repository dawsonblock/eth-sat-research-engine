"""Bounded geometric Cauchy modes at a residue-field interpolation point.

Coefficients are evaluated at T=t+2^(a+1)*zeta in the finite extension
ring.  Even factors are cancelled as integer powers of two before a unit is
inverted. This is a finite reference, not the uniform mode-count theorem.
"""
from __future__ import annotations

from collections import defaultdict

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_interpolation.extension_lagrange import evaluate_polynomial
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value
from veritas.research.eth_modes_v27.enumeration import count_tuples, ModeBudgetExceeded
from veritas.research.eth_modes_v31.jet_tiles import _v2
from veritas.research.eth_packing_v26.checker import verify_d3_packing
from veritas.research.eth_packing_v26.implicit import check_implicit_mode_source
from .structural_tuples import structural_tuples


SCHEMA = 'VERITAS_ETH_POINT_MODES_V39'
CLAIM = 'FINITE_GEOMETRIC_POINT_MODES_ONLY'
SCOPE = {'point_evaluation': True, 'full_recursive_contraction': False,
         'subexponential_runtime_proven': False}


def _source_check(source):
    if not isinstance(source, dict):
        raise ValueError('D.3 packet source required')
    if source.get('schema') == 'VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1':
        result = check_implicit_mode_source(source)
    else:
        result = verify_d3_packing(source, check_trace=True)
    if result.get('valid') is not True:
        raise ValueError('D.3 packet source did not verify')


def _inputs(source, node, precision, extension_degree, zeta):
    _source_check(source)
    if any(type(x) is not int for x in (node, precision, extension_degree)):
        raise ValueError('integer point-mode parameters required')
    L = source['L']
    if not (1 <= source['M'] <= 6 and L in (2, 4) and source['r'] <= 4 and
            2 <= precision <= 1024 and 1 <= extension_degree <= 8):
        raise ValueError('finite point-mode parameter limit exceeded')
    if not (-L <= node < L and node != 0 and _v2(node) < source['a']):
        raise ValueError('invalid active node')
    ring = ExtensionRing(precision, first_irreducible(extension_degree))
    if (not isinstance(zeta, (tuple, list)) or len(zeta) != ring.e or
            any(type(v) is not int or not 0 <= v < ring.modulus for v in zeta)):
        raise ValueError('interpolation point is not a canonical extension-ring value')
    return ring, tuple(zeta)


def _cauchy_value(L, node, ring, x, y, zeta):
    return cauchy_point_value(L, node, ring, x, y, zeta)


def _reference_cauchy_value(L, node, ring, x, y, zeta):
    return evaluate_polynomial(ring, shift_cauchy_entry(L, node, ring, x, y), zeta)


def make_point_modes(source, *, node=1, precision=5, extension_degree=3,
                     zeta=None, max_modes=240, max_tuples=6000):
    """Generate a checked finite geometric decomposition at one point."""
    if zeta is None:
        zeta = (0,) * extension_degree
    ring, zeta = _inputs(source, node, precision, extension_degree, zeta)
    if type(max_modes) is not int or not 0 <= max_modes <= 240:
        raise ValueError('invalid mode budget')
    if type(max_tuples) is not int or not 1 <= max_tuples <= 100_000:
        raise ValueError('invalid structural tuple budget')
    L = source['L']
    coordinate = _v2(node)
    B = 1 << (coordinate + 1)
    alpha = 2 * L
    modes, local, crosses = [], [], []
    for packet_id, packet in enumerate(source['packets']):
        real = [(slot, eid) for slot, eid in enumerate(packet['slots']) if eid is not None]
        tiles = defaultdict(list)
        for y, cid in real:
            y0 = y % B
            tiles[y0].append((cid, (y - y0) // B))
        for x, rid in real:
            rg = source['row_labels'][str(source['edges'][rid][0])][coordinate]
            for y, cid in real:
                cg = source['column_labels'][str(source['edges'][cid][1])][coordinate]
                if rg == cg:
                    value = _cauchy_value(L, node, ring, x, y, zeta)
                    if value != ring.zero:
                        local.append([rid, cid, [list(value)]])
                else:
                    crosses.append([rid, cid])
        for y0, columns in sorted(tiles.items()):
            source_groups = {source['column_labels'][str(source['edges'][cid][1])][coordinate]
                             for cid, _ in columns}
            if len(source_groups) != 1:
                raise ArithmeticError('tile columns do not share a source group')
            source_group = next(iter(source_groups))
            for target_group in range(source['r']):
                if target_group == source_group:
                    continue
                targets = [(x, rid) for x, rid in real
                           if source['row_labels'][str(source['edges'][rid][0])][coordinate] == target_group]
                if not targets:
                    continue
                for b in range(precision - 1):
                    terms = [[cid, j ** b] for cid, j in columns if j ** b]
                    if not terms:
                        continue
                    rows = []
                    for x, rid in targets:
                        d = node - y0 + x
                        if d == 0 or _v2(d) > coordinate:
                            raise ArithmeticError('invalid cross-tile denominator valuation')
                        v = _v2(d)
                        unit = ring.add(ring.elem([d // (1 << v)]),
                                        ring.mul(ring.elem([alpha // (1 << v)]), zeta))
                        if not ring.is_unit(unit):
                            raise ArithmeticError('cross-tile denominator is not a unit after cancellation')
                        ratio = ring.mul(ring.elem([B // (1 << v)]), ring.inverse(unit))
                        value = ring.mul(_cauchy_value(L, node, ring, x, y0, zeta),
                                         ring.pow(ratio, b))
                        if value != ring.zero:
                            if ring.valuation(value) < b + 1:
                                raise ArithmeticError('point mode violates the required valuation')
                            rows.append([rid, [list(value)]])
                    if rows:
                        if len(modes) >= max_modes:
                            raise ModeBudgetExceeded('point-mode budget exhausted')
                        modes.append({'packet': packet_id, 'tile_residue': y0,
                                      'exponent': b, 'weight': b + 1,
                                      'source_group': source_group, 'target_group': target_group,
                                      'rows': rows, 'column_terms': terms})
    # Every exponent is below precision, so precision**len(modes) bounds the
    # nominal count. Count it exactly without rejecting an otherwise small
    # structurally nonzero set. The integer bound has at most 2641 bits here.
    nominal_cap = 1 << (len(modes) * precision.bit_length())
    tuple_count = count_tuples([mode['weight'] for mode in modes], precision, cap=nominal_cap)
    structural_count = sum(1 for _ in structural_tuples(modes, precision, max_tuples=max_tuples))
    return {'schema': SCHEMA, 'claim': CLAIM, 'scope': dict(SCOPE),
            'd3_certificate': source, 'node': node, 'precision': precision,
            'extension_degree': extension_degree, 'jet_length': 1,
            'irreducible_polynomial': ring.f, 'zeta': list(zeta),
            'local': local, 'cross_pairs': sorted(crosses), 'modes': modes,
            'mode_tuple_count': tuple_count, 'structural_tuple_count': structural_count}


def check_point_modes(cert):
    """Check every reconstructed Cauchy entry and replay the mode list."""
    try:
        if (not isinstance(cert, dict) or cert.get('schema') != SCHEMA or
                cert.get('claim') != CLAIM or cert.get('scope') != SCOPE or
                cert.get('jet_length') != 1):
            raise ValueError('unsupported point-mode certificate')
        source, node, p, degree = (cert['d3_certificate'], cert['node'],
                                    cert['precision'], cert['extension_degree'])
        ring, zeta = _inputs(source, node, p, degree, cert['zeta'])
        if cert['irreducible_polynomial'] != ring.f:
            raise ValueError('extension polynomial mismatch')
        reference = {}
        for packet in source['packets']:
            real = [(slot, eid) for slot, eid in enumerate(packet['slots']) if eid is not None]
            for x, rid in real:
                for y, cid in real:
                    reference[(rid, cid)] = _reference_cauchy_value(source['L'], node, ring, x, y, zeta)
        reconstructed = {key: ring.zero for key in reference}
        for rid, cid, encoded in cert['local']:
            key = (rid, cid)
            if key not in reconstructed:
                raise ValueError('local entry is outside a packet')
            reconstructed[key] = ring.add(reconstructed[key], ring.elem(encoded[0]))
        for mode in cert['modes']:
            for rid, encoded in mode['rows']:
                coefficient = ring.elem(encoded[0])
                if ring.valuation(coefficient) < mode['weight']:
                    raise ValueError('mode coefficient fails its divisibility bound')
                for cid, power in mode['column_terms']:
                    key = (rid, cid)
                    if key not in reconstructed:
                        raise ValueError('mode crosses distinct packets')
                    reconstructed[key] = ring.add(reconstructed[key],
                                                  ring.mul(coefficient, ring.elem([power])))
        if reconstructed != reference:
            raise ValueError('mode expansion does not reconstruct the Cauchy matrix')
        structural_count = cert.get('structural_tuple_count')
        if type(structural_count) is not int or not 1 <= structural_count <= 100_000:
            raise ValueError('invalid structural tuple count')
        expected = make_point_modes(source, node=node, precision=p,
                                    extension_degree=degree, zeta=zeta,
                                    max_tuples=max(6000, structural_count))
        if expected != cert:
            raise ValueError('point-mode certificate differs from canonical replay')
        return {'valid': True, 'status': 'FINITE_POINT_MODES_REPLAYED',
                'mode_count': len(cert['modes']), 'subexponential_runtime_proven': False}
    except (ValueError, TypeError, KeyError, IndexError, OverflowError,
            ArithmeticError, ZeroDivisionError) as exc:
        return {'valid': False, 'status': 'INVALID_POINT_MODES', 'reason': str(exc)}

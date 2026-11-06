"""Exact zero-wire leaf certificates for immutable described networks.

The verifier replays the input entries and uses a separately implemented
coordinate-wise polynomial multiplication. This proves only the supplied
finite leaf contraction, not its connection to an arbitrary CNF or any
asymptotic complexity claim.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from .described_network import CreatedDenseTensor, CreatedPacketTensor, DescribedNetwork
from .lazy_children import ChildEvaluationBudgetExceeded, _Budget

SCHEMA = 'VERITAS_ETH_ZERO_WIRE_LEAF_V1'
_CERTIFICATE_FIELDS = {'schema', 'precision', 'defining_polynomial', 'jet_length',
                       'input_description_sha256', 'factors', 'result', 'scope'}


def _ring(network, precision, empty_polynomial=None, empty_jet_length=1):
    if not isinstance(network, DescribedNetwork) or network.edges != 0:
        raise ValueError('a zero-wire described network is required')
    if type(precision) is not int or precision < 1:
        raise ValueError('positive integer target precision required')
    if precision > 1024:
        raise ChildEvaluationBudgetExceeded('zero-wire precision exceeds finite ring limit')
    shape = None
    for vertex in network.vertices:
        tensor = vertex.tensor
        if isinstance(tensor, CreatedDenseTensor):
            entry = tensor.entries[0]
            item = (entry.defining_polynomial, len(entry.coefficients), entry.creation_precision)
        elif isinstance(tensor, CreatedPacketTensor):
            item = (tensor.defining_polynomial, tensor.jet_length, tensor.creation_precision)
        else:
            raise ValueError('unsupported zero-wire tensor description')
        if shape is not None and item[:2] != shape[:2]:
            raise ValueError('incompatible tensor entry rings')
        shape = item if shape is None else (shape[0], shape[1], max(shape[2], item[2]))
    if shape is None:
        polynomial = first_irreducible(1) if empty_polynomial is None else empty_polynomial
        if type(polynomial) is not int or polynomial.bit_length() > 9:
            raise ValueError('empty-network extension degree must be at most eight')
        return JetRing(ExtensionRing(precision, polynomial), empty_jet_length)
    if precision < shape[2]:
        raise ValueError('target precision precedes a tensor creation')
    return JetRing(ExtensionRing(precision, shape[0]), shape[1])


def _digest(network):
    data = json.dumps(asdict(network), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('ascii')
    return sha256(data).hexdigest()


def _encoded(value):
    return [list(coordinate) for coordinate in value]


def _same_json(left, right):
    return (json.dumps(left, sort_keys=True, separators=(',', ':'), allow_nan=False) ==
            json.dumps(right, sort_keys=True, separators=(',', ':'), allow_nan=False))


def make_zero_wire_certificate(network, *, target_precision, max_work=250_000,
                               timeout_s=10.0, empty_polynomial=None,
                               empty_jet_length=1):
    """Make a bounded certificate; raise on resource exhaustion."""
    budget = _Budget(max_work, timeout_s)
    budget.tick()
    ring = _ring(network, target_precision, empty_polynomial, empty_jet_length)
    factors = []
    value = ring.one
    for vertex in network.vertices:
        budget.tick()
        factor = vertex.tensor.evaluate((), ring, budget)
        value = ring.mul(value, factor)
        factors.append({'side': vertex.side, 'label': vertex.label,
                        'value': _encoded(factor)})
    cert = {'schema': SCHEMA, 'precision': target_precision,
            'defining_polynomial': ring.base.f, 'jet_length': ring.length,
            'input_description_sha256': _digest(network),
            'factors': factors, 'result': _encoded(value),
            'scope': 'FINITE_ZERO_WIRE_LEAF_ONLY'}
    budget.tick()
    return {'certificate': cert, 'work_units': budget.used}


def _independent_product(left, right, *, precision, polynomial, length):
    """Multiply jets using direct bivariate convolution and polynomial reduction."""
    degree = polynomial.bit_length() - 1
    modulus = 1 << precision
    output = [[0] * degree for _ in range(length)]
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            if i + j >= length:
                continue
            terms = [0] * (2 * degree - 1)
            for x, avalue in enumerate(a):
                for y, bvalue in enumerate(b):
                    terms[x + y] += avalue * bvalue
            for power in range(2 * degree - 2, degree - 1, -1):
                coefficient = terms[power]
                for low in range(degree):
                    if polynomial >> low & 1:
                        terms[power - degree + low] -= coefficient
            for x in range(degree):
                output[i + j][x] = (output[i + j][x] + terms[x]) % modulus
    return tuple(tuple(row) for row in output)


def check_zero_wire_certificate(network, certificate, *, max_work=250_000,
                                timeout_s=10.0):
    """Recheck every input entry and independently multiply the lifted jets."""
    try:
        budget = _Budget(max_work, timeout_s)
        budget.tick()
        if (type(certificate) is not dict or certificate.get('schema') != SCHEMA or
                certificate.get('scope') != 'FINITE_ZERO_WIRE_LEAF_ONLY' or
                set(certificate) != _CERTIFICATE_FIELDS):
            raise ValueError('unsupported zero-wire certificate')
        p = certificate['precision']
        polynomial = certificate['defining_polynomial']
        length = certificate['jet_length']
        ring = _ring(network, p, polynomial, length)
        if (ring.base.f != polynomial or ring.length != length or
                certificate.get('input_description_sha256') != _digest(network)):
            raise ValueError('certificate does not bind to the input ring and description')
        factors = certificate['factors']
        if type(factors) is not list or len(factors) != len(network.vertices):
            raise ValueError('incorrect zero-wire factor count')
        result = ring.one
        for vertex, recorded in zip(network.vertices, factors):
            budget.tick()
            factor = vertex.tensor.evaluate((), ring, budget)
            expected = {'side': vertex.side, 'label': vertex.label, 'value': _encoded(factor)}
            if not _same_json(recorded, expected):
                raise ValueError('zero-wire factor does not match its source entry')
            result = _independent_product(result, factor, precision=p,
                                          polynomial=polynomial, length=length)
        if not _same_json(certificate.get('result'), _encoded(result)):
            raise ValueError('zero-wire product differs from the certificate')
        budget.tick()
        return {'valid': True, 'status': 'FINITE_ZERO_WIRE_LEAF_VERIFIED',
                'work_units': budget.used, 'result': result,
                'asymptotic_runtime_proven': False}
    except ChildEvaluationBudgetExceeded as exc:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc)}
    except (TypeError, ValueError, KeyError, IndexError, OverflowError) as exc:
        return {'valid': False, 'status': 'INVALID_ZERO_WIRE_CERTIFICATE', 'reason': str(exc)}

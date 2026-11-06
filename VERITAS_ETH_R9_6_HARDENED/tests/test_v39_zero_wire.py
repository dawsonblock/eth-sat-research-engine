from copy import deepcopy

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.boolean_count import recover_boolean_count
from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39 import (
    check_zero_wire_certificate, describe_integer_network,
    make_zero_wire_certificate, run_tapered_finite,
)
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedDenseTensor, DescribedNetwork, DescribedVertex,
)


@pytest.mark.parametrize('n,clauses,expected', [
    (0, [], 1),
    (0, [[]], 0),
    (3, [], 8),
    (3, [[]], 0),
    (3, [[], []], 0),
])
def test_zero_wire_cnf_counts_and_replayable_certificates(n, clauses, expected):
    net = from_cnf(CNF.from_lists(n, clauses))
    assert net.edges == 0
    described = describe_integer_network(net, creation_precision=n + 1,
                                         defining_polynomial=first_irreducible(3))
    result = run_tapered_finite(described, target_precision=n + 1)
    assert result['status'] == 'FINITE_ZERO_WIRE_LEAF_VERIFIED'
    assert result['recursive_levels_exercised'] == 0
    assert result['result'][0][0] == expected
    assert all(x == 0 for x in result['result'][0][1:])
    assert recover_boolean_count(result['result'][0][0], precision=n + 1,
                                 num_variables=n) == expected
    assert check_zero_wire_certificate(described, result['certificate'])['valid']


def test_zero_wire_certificate_rejects_tampering_and_different_source():
    described = describe_integer_network(from_cnf(CNF.from_lists(2, [])),
                                         creation_precision=3,
                                         defining_polynomial=first_irreducible(3))
    cert = make_zero_wire_certificate(described, target_precision=3)['certificate']
    other = describe_integer_network(from_cnf(CNF.from_lists(1, [])),
                                     creation_precision=3,
                                     defining_polynomial=first_irreducible(3))
    assert not check_zero_wire_certificate(other, cert)['valid']
    for mutation in ('factor', 'result', 'boolean_factor', 'digest', 'precision', 'extra_claim'):
        bad = deepcopy(cert)
        if mutation == 'factor':
            bad['factors'][0]['value'][0][0] ^= 1
        elif mutation == 'boolean_factor':
            bad['factors'][0]['value'][0][1] = False
        elif mutation == 'result':
            bad['result'][0][0] ^= 1
        elif mutation == 'digest':
            bad['input_description_sha256'] = '0' * 64
        elif mutation == 'extra_claim':
            bad['subexponential_runtime_proven'] = True
        else:
            bad['precision'] = 2
        assert not check_zero_wire_certificate(described, bad)['valid']


def test_zero_wire_extension_jet_product_and_creation_lift():
    # U^2 = -U-1.  The first factor captures 7 modulo 8, then is lifted;
    # it must not be recomputed as -1 modulo 32.
    source = JetRing(ExtensionRing(3, 0b111), 2)
    entries = (source.elem([[7, 1], [0, 1]]),
               source.elem([[1, 1], [2, 0]]))
    network = DescribedNetwork(0, tuple(
        DescribedVertex('row', f'row:{i}', (),
                        CreatedDenseTensor(0, (CreationJetEntry.capture(source, entry),)))
        for i, entry in enumerate(entries)
    ))
    result = run_tapered_finite(network, target_precision=5)
    # (7+U+UV)(1+U+2V) = 6+7U + (13+2U)V modulo (32,U^2+U+1,V^2).
    assert result['result'] == ((6, 7), (13, 2))
    assert check_zero_wire_certificate(network, result['certificate'])['valid']


def test_zero_wire_and_oversize_budgets_fail_without_a_result():
    zero = describe_integer_network(from_cnf(CNF.from_lists(0, [])),
                                    creation_precision=1,
                                    defining_polynomial=first_irreducible(1))
    assert run_tapered_finite(zero, target_precision=1, max_work=1)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    cert = make_zero_wire_certificate(zero, target_precision=1)['certificate']
    verdict = check_zero_wire_certificate(zero, cert, max_work=1)
    assert verdict['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in verdict
    too_large = describe_integer_network(from_cnf(CNF.from_lists(8, [list(range(1, 9))])),
                                         creation_precision=9,
                                         defining_polynomial=first_irreducible(3))
    result = run_tapered_finite(too_large, target_precision=9)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result

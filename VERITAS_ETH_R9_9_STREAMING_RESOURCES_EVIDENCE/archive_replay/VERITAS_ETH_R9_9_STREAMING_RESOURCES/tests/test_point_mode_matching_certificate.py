from copy import deepcopy

import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.independent_tuple_oracle import direct_tuple_contribution
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.point_mode_matching import (
    certify_point_mode_matching_zero, replay_point_mode_matching_zero,
)
from veritas.research.tensor import from_cnf


def fixture():
    network = from_cnf(CNF.from_lists(2, [[1, 2]]))
    parent = describe_integer_network(network, creation_precision=3,
                                      defining_polynomial=first_irreducible(3))
    source = implicit_mode_source(construct_implicit_packing(parent.bipartite_edges(), r=2, a=1))
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3, zeta=(1, 0, 0))
    assert len(modes['modes']) == 1 and len(modes['modes'][0]['rows']) == 1
    return parent, modes


def test_checked_support_zero_replays_and_matches_independent_oracle():
    parent, modes = fixture()
    result = certify_point_mode_matching_zero(modes, (2,))
    assert result['valid'] and result['status'] == 'FINITE_STRUCTURAL_ZERO_CERTIFIED'
    assert result['support_provenance_verified'] and not result['mode_validation_work_metered']
    assert not result['uniform_complexity_proven']
    certificate = result['certificate']
    assert certificate['witness']['demand'] == 2
    assert certificate['witness']['available_rows'] == 1
    assert replay_point_mode_matching_zero(modes, certificate)['valid']
    assert direct_tuple_contribution(parent, modes, (2,))['result'] == ((0, 0, 0),)


def test_feasible_support_never_claims_a_nonzero_coefficient():
    _, modes = fixture()
    result = certify_point_mode_matching_zero(modes, (1,))
    assert result['valid'] and result['status'] == 'MATCHING_FEASIBLE_ONLY'
    assert not result['nonzero_proven'] and 'certificate' not in result


@pytest.mark.parametrize('beta', [(), (-1,), (True,), (1, 2)])
def test_invalid_beta_is_rejected(beta):
    _, modes = fixture()
    assert certify_point_mode_matching_zero(modes, beta)['status'] == 'INVALID_WEIGHTED_TUPLE'


def test_tampered_modes_and_hall_certificates_are_rejected():
    _, modes = fixture()
    certificate = certify_point_mode_matching_zero(modes, (2,))['certificate']
    bad_modes = deepcopy(modes)
    bad_modes['modes'][0]['weight'] += 1
    assert not certify_point_mode_matching_zero(bad_modes, (2,))['valid']
    assert not replay_point_mode_matching_zero(bad_modes, certificate)['valid']
    for mutate in ('hash', 'beta', 'demand', 'row', 'extra'):
        bad = deepcopy(certificate)
        if mutate == 'hash':
            bad['mode_certificate_sha256'] = '0' * 64
        elif mutate == 'beta':
            bad['beta'] = [1]
        elif mutate == 'demand':
            bad['witness']['demand'] += 1
        elif mutate == 'row':
            bad['witness']['row_ids'].append(99)
        else:
            bad['universal_theorem_proven'] = True
        assert not replay_point_mode_matching_zero(modes, bad)['valid']


def test_work_and_mode_replay_exhaustion_return_inconclusive(monkeypatch):
    from veritas.research.eth_recursive_contraction_v39 import point_mode_matching

    _, modes = fixture()
    certificate = certify_point_mode_matching_zero(modes, (2,))['certificate']
    result = certify_point_mode_matching_zero(modes, (2,), max_work=1)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'certificate' not in result
    result = replay_point_mode_matching_zero(modes, certificate, max_work=1)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and not result['valid']
    monkeypatch.setattr(point_mode_matching, 'check_point_modes',
                        lambda *args, **kwargs: {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'})
    result = certify_point_mode_matching_zero(modes, (2,))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'certificate' not in result
    assert replay_point_mode_matching_zero(modes, certificate)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'

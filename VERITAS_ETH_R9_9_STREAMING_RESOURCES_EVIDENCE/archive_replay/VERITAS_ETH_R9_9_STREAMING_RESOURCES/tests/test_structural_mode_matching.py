from itertools import product
from random import Random

import pytest

from veritas.research.eth_recursive_contraction_v39.mode_matching import (
    certify_structural_tuple_matching,
)


def mode(packet, target, rows):
    return {'packet': packet, 'target_group': target,
            'rows': [[row, [[1]]] for row in rows]}


def brute_feasible(modes, beta):
    groups = {(m['packet'], m['target_group']) for m in modes}
    for key in groups:
        choices = [tuple(row[0] for row in m['rows'])
                   for m, b in zip(modes, beta)
                   if (m['packet'], m['target_group']) == key
                   for _ in range(b)]
        if not any(len(set(selected)) == len(selected) for selected in product(*choices)):
            return False
    return True


def test_hall_obstruction_detects_case_aggregate_capacity_misses():
    # Three target rows in total, but two demanded modes can only use row 0.
    modes = [mode(0, 0, [0]), mode(0, 0, [0]), mode(0, 0, [1, 2])]
    result = certify_structural_tuple_matching(modes, (1, 1, 0))
    assert result['status'] == 'ZERO_IF_SUPPLIED_SUPPORT_COMPLETE'
    assert result['witness'] == {'packet': 0, 'target_group': 0,
                                 'mode_indices': [0, 1], 'row_ids': [0],
                                 'demand': 2, 'available_rows': 1}
    assert not result['support_provenance_verified']


def test_matching_agrees_with_independent_assignment_enumeration():
    rng = Random(20261102)
    for _ in range(350):
        n = rng.randrange(6)
        modes = [mode(rng.randrange(2), rng.randrange(2),
                      [row for row in range(3) if rng.randrange(2)])
                 for _ in range(n)]
        beta = tuple(rng.randrange(3) for _ in range(n))
        expected = brute_feasible(modes, beta)
        result = certify_structural_tuple_matching(modes, beta)
        assert (result['status'] == 'MATCHING_FEASIBLE_ONLY') == expected
        if not expected:
            witness = result['witness']
            indices = witness['mode_indices']
            neighbors = {row[0] for index in indices for row in modes[index]['rows']}
            assert all((modes[i]['packet'], modes[i]['target_group']) ==
                       (witness['packet'], witness['target_group']) for i in indices)
            assert sorted(neighbors) == witness['row_ids']
            assert sum(beta[i] for i in indices) == witness['demand'] > len(neighbors)
        else:
            assert not result['nonzero_proven']
            for group in result['group_matchings']:
                rows = [row for assignment in group['assigned_rows'].values() for row in assignment]
                assert len(rows) == len(set(rows))
                for index, assigned in group['assigned_rows'].items():
                    assert len(assigned) == beta[index]
                    assert set(assigned) <= {item[0] for item in modes[index]['rows']}


def test_feasible_matching_does_not_claim_coefficient_nonzero():
    # [z] (1+z)(1-z) = 0 over the integers despite two valid selections.
    result = certify_structural_tuple_matching([mode(0, 0, [0, 1])], (1,))
    assert result['status'] == 'MATCHING_FEASIBLE_ONLY'
    assert not result['nonzero_proven']


def test_work_exhaustion_is_inconclusive_and_has_no_partial_witness():
    result = certify_structural_tuple_matching([mode(0, 0, [0])], (1,), max_work=1)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert result['work_units'] == 1
    assert 'witness' not in result and 'zero_from_supplied_support' not in result


def test_many_modes_do_not_use_python_recursion():
    modes = [mode(0, 0, [i]) for i in range(1200)]
    result = certify_structural_tuple_matching(modes, (1,) * len(modes))
    assert result['status'] == 'MATCHING_FEASIBLE_ONLY'
    assert len(result['group_matchings'][0]['assigned_rows']) == 1200


@pytest.mark.parametrize('modes,beta', [
    ([mode(0, 0, [0])], (-1,)),
    ([mode(0, 0, [0, 0])], (1,)),
    ([mode(0, 0, [True])], (1,)),
    ([mode(0, 0, [0])], (True,)),
    ([mode(0, 0, [0])], ()),
])
def test_invalid_metadata_is_rejected(modes, beta):
    with pytest.raises(ValueError):
        certify_structural_tuple_matching(modes, beta)

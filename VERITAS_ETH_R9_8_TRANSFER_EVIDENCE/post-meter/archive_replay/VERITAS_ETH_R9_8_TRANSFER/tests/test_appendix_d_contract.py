from dataclasses import replace
import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork, from_cnf
from veritas.research.appendix_d_contract import (
    SOURCE_REVISION, bind_tensor_call, validate_tensor_call,
)


def test_contract_binds_immutable_input_and_finite_resource_model():
    net = from_cnf(CNF.from_lists(1, [[1]]))
    contract = bind_tensor_call(
        net, size_parameter=2, description_length=100_000, depth=0,
        size_constant=1, root_precision=8, precision=8,
        truncation_order=2, precision_path=(8,))
    result = validate_tensor_call(net, contract)
    assert result['valid']
    assert result['manuscript_revision'] == SOURCE_REVISION
    assert result['ring'] == '(Z/2^P Z)[V]/(V^ell)'
    assert result['schedule']['status'] == 'DIRECT_LEAF_ALLOWED'
    assert not result['universal_theorem_proven']

    changed = from_cnf(CNF.from_lists(1, [[-1]]))
    assert validate_tensor_call(changed, contract)['status'] == 'INVALID_CREATION_DESCRIPTION'


def test_contract_rejects_unpinned_revision_and_bad_precision_path():
    net = from_cnf(CNF.from_lists(1, [[1]]))
    contract = bind_tensor_call(
        net, size_parameter=2, description_length=100_000, depth=0,
        size_constant=1, root_precision=8, precision=8,
        truncation_order=2, precision_path=(8,))
    try:
        replace(contract, manuscript_revision='moving-main')
    except ValueError as exc:
        assert 'revision' in str(exc)
    else:
        raise AssertionError('unpinned revision accepted')

    try:
        replace(contract, precision_path=(7,))
    except ValueError as exc:
        assert 'precision path' in str(exc)
    else:
        raise AssertionError('inconsistent precision path accepted')


def test_contract_reports_resource_exhaustion_as_inconclusive():
    net = from_cnf(CNF.from_lists(1, [[1]]))
    contract = bind_tensor_call(
        net, size_parameter=2, description_length=100_000, depth=0,
        size_constant=1, root_precision=8, precision=8,
        truncation_order=2, max_table_entries=1, precision_path=(8,))
    assert validate_tensor_call(net, contract)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'


def test_precision_increases_and_each_entry_is_lifted_from_its_own_creation_precision():
    net = TensorNetwork(1, (Factor((0,), (-1, 0), 'row:0'),
                            Factor((0,), (-1, 1), 'col:0')))
    contract = bind_tensor_call(
        net, size_parameter=8, description_length=100_000, depth=1,
        size_constant=1, root_precision=3, precision=5,
        truncation_order=1, precision_path=(3, 5),
        entry_creation_precisions=(3, 5))
    result = validate_tensor_call(net, contract)
    assert result['valid']
    # -1 at precision 3 lifts as 7, not as -1 modulo 32 (31).
    assert result['canonical_entry_lifts'] == ((7, 0), (31, 1))
    assert result['entry_creation_precisions'] == (3, 5)

    for path in ((3, 3), (5, 3), (4, 5)):
        with pytest.raises(ValueError, match='precision path'):
            replace(contract, precision_path=path)
    with pytest.raises(ValueError, match='creation precisions'):
        replace(contract, entry_creation_precisions=(4, 5))
    assert validate_tensor_call(net, replace(contract, max_precision_bits=4))['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'

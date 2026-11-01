from random import Random

import pytest

from veritas.research.dense_cauchy_testbed import (
    DenseWorkLimit, _kernel, experiment, reconstruct_zero)
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials, evaluate


def dense_tables(wires):
    rng = Random(381 + wires)
    return ([rng.randrange(2) for _ in range(1 << wires)],
            [rng.randrange(2) for _ in range(1 << wires)])


def test_kernel_matches_independently_constructed_polynomials():
    polynomial = cauchy_matrix_polynomials(2)
    for node in range(-12,13):
        assert _kernel(node) == tuple(tuple(evaluate(c, node) for c in row) for row in polynomial)
    assert _kernel(0) == ((1, 0), (0, 1))


@pytest.mark.parametrize('wires', [8, 16])
def test_dense_weighted_modes_reconstruct_packet_deformation(wires):
    a, b = dense_tables(wires)
    result = experiment(a, b, wires, precision=2)
    assert result['original_count_modulus'] == sum(x*y for x,y in zip(a,b)) % 4
    assert result['deformed_value_modulus'] == sum(m['contribution'] for m in result['modes']) % 4
    assert result['retained_structural_modes'] == 1+wires
    assert result['discarded_structural_modes'] == 2**wires-1-wires
    assert result['largest_child_wires'] == wires
    assert result['complexity_or_theorem_proven'] is False
    assert result['counted_scalar_additions'] + result['counted_scalar_multiplications'] > 2 * 2**wires
    if wires == 8:
        assert result['direct_halfedge_status'] == 'checked'
        assert result['direct_halfedge_value'] == result['deformed_value_modulus']
    else:
        assert result['direct_halfedge_status'] == 'BLOCKED_PAIR_CAP'
        assert result['direct_halfedge_value'] is None


def test_fail_closed_on_input_and_work_guards():
    a, b = dense_tables(8)
    with pytest.raises(DenseWorkLimit):
        experiment(a, b, 8, max_ops=1)
    with pytest.raises(ValueError):
        experiment(a[:-1], b, 8)
    with pytest.raises(ValueError):
        experiment(a, b, 8, precision=0)
    with pytest.raises(ValueError):
        experiment(a, b, 9)


def test_ten_wire_modulo_two_identity():
    a, b = dense_tables(10)
    result = experiment(a, b, 10, precision=1)
    assert result['deformed_value_modulus'] == result['original_count_modulus']
    assert result['retained_structural_modes'] == 1
    assert result['direct_halfedge_status'] == 'BLOCKED_PAIR_CAP'


def test_nonzero_node_hermite_reconstructs_original_dense_count():
    a,b=dense_tables(8)
    result=reconstruct_zero(a,b,8,precision=2)
    assert result['status']=='EXACT_HERMITE_RECONSTRUCTION_CHECKED'
    assert result['nodes_and_multiplicities']==[
        {'node':-2,'multiplicity':9},
        {'node':-1,'multiplicity':8},
        {'node':1,'multiplicity':8},
    ]
    assert result['guard_bits']==13
    assert result['input_jet_precision_bits']==15
    assert result['reconstructed_at_zero']==result['independent_original_contraction']
    assert result['estimated_scalar_operations']>=result['counted_scalar_operations']
    assert result['independent_jet_evaluation_status']=='checked'
    assert len(result['independent_jet_evaluation_checks'])==6
    assert result['manuscript_tapered_recurrence_implemented'] is False
    assert result['subexponential_bound_proven'] is False


def test_zero_reconstruction_fails_closed_at_dense_resource_cap():
    a,b=dense_tables(16)
    with pytest.raises(DenseWorkLimit,match='cap'):
        reconstruct_zero(a,b,16,precision=2)


def test_ten_wire_hermite_reconstruction_uses_exact_guard_precision():
    a,b=dense_tables(10)
    result=reconstruct_zero(a,b,10,precision=2)
    assert result['guard_bits']==17
    assert result['input_jet_precision_bits']==19
    assert result['reconstructed_at_zero']==result['independent_original_contraction']
    assert result['independent_jet_evaluation_status']=='BLOCKED_PAIR_CAP'

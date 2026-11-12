from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
from veritas.research.gf2_xor_mixed import exhaustive_mixed_count


def test_multi_xor_auto_uses_conditioning_after_reject():
    cnf = CNF.from_lists(3, [[3]])
    eqs = (XorEquation((1, 2), 1), XorEquation((2, 3), 0))
    assert exhaustive_mixed_count(cnf, eqs) == 1
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, verify_direct=True)
    assert out['count'] == '1'
    assert out['independent_count_checked'] is True
    assert out['engine'] == 'MIXED_XOR_CONDITIONING'
    stages = [s.get('stage') for s in out['pipeline']['steps']]
    assert 'xor_mixed_conditioning' in stages
    assert 'xor_substitute' not in stages


def test_mixed_cross_check_xor_aware():
    cnf = CNF.from_lists(3, [[1, 3]])
    eqs = (XorEquation((1, 2), 1),)
    out = structure_with_optional_xor(
        cnf, xor_equations=eqs, preprocess=False, verify_direct=True, xor_strategy='condition'
    )
    assert out['count'] == '3'
    assert out['independent_count_checked'] is True
    assert out['structure']['cross_check']['reference_count'] == '3'


def test_binary_substitute_still_fast_path():
    cnf = CNF.from_lists(3, [[1, 3]])
    eqs = (XorEquation((1, 2), 1),)
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, verify_direct=True)
    assert out['count'] == '3'
    assert out['independent_count_checked'] is True
    assert 'XOR_BINARY' in out['engine']

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
from veritas.research.gf2_xor_mixed import count_mixed_xor_cnf
from veritas.solvers.reference import exhaustive_count


def test_mixed_xor_and_cnf_conditioning():
    eqs = (XorEquation((1, 2), 1),)
    cnf = CNF.from_lists(3, [[1, 3]])
    assert count_mixed_xor_cnf(cnf, eqs)['count'] == 3
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, verify_direct=False)
    assert out['count'] == '3'
    assert out['engine'] == 'MIXED_XOR_CONDITIONING'


def test_inconsistent_mixed_is_zero():
    eqs = (XorEquation((1,), 0), XorEquation((1,), 1))
    cnf = CNF.from_lists(2, [[1, 2]])
    assert count_mixed_xor_cnf(cnf, eqs)['count'] == 0

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
from veritas.research.gf2_xor_encode import encode_xor_equations, count_via_xor_encoding
from veritas.research.gf2_xor_mixed import exhaustive_mixed_count


def test_encode_matches_exhaustive_small():
    cnf = CNF.from_lists(3, [[1, 3]])
    eqs = (XorEquation((1, 2), 1),)
    assert exhaustive_mixed_count(cnf, eqs) == 3
    enc, _ = encode_xor_equations(cnf, eqs)
    assert enc.n >= 3
    out = count_via_xor_encoding(cnf, eqs)
    assert int(out['count']) == 3
    pipe = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, xor_strategy='encode')
    assert pipe['count'] == '3'


def test_auto_encode_when_enum_budget_exceeded():
    from veritas.research.gf2_xor_mixed import xor_parametrization

    cnf = CNF.from_lists(22, [[1, 2]])
    eqs = (XorEquation(tuple(range(1, 23)), 0),)
    assert len(xor_parametrization(eqs, 22).free_variables) > 4
    out = structure_with_optional_xor(
        cnf,
        xor_equations=eqs,
        preprocess=False,
        max_xor_enum_bits=4,
        xor_strategy='auto',
        verify_direct=False,
        timeout_s=15,
    )
    assert 'XOR_CNF_ENCODE' in out.get('engine', '')
    assert 'xor_cnf_encode' in {s['stage'] for s in out['pipeline']['steps']}

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
from veritas.research.gf2_xor_substitute import substitute_binary_xor, try_xor_algebraic_reduce

def test_binary_substitute_reindexes():
    cnf = CNF.from_lists(3, [[2, 3]])
    eqs = (XorEquation((1, 2), 1),)
    reduced, eqs2, sub = substitute_binary_xor(cnf, eqs)
    assert sub['changed'] and reduced.n == 2
    assert not eqs2


def test_auto_pipeline_matches_exhaustive():
    cnf = CNF.from_lists(3, [[1, 3]])
    eqs = (XorEquation((1, 2), 1),)
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False)
    assert out['count'] == '3'
    assert 'XOR_BINARY' in out.get('engine', '') or out.get('substitute_report')


def test_algebraic_reduce_explicit():
    cnf = CNF.from_lists(3, [[2, 3]])
    out = try_xor_algebraic_reduce(cnf, (XorEquation((1, 2), 1),))
    assert out is not None
    assert int(out['count']) == 3

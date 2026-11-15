from veritas.research.gf2_xor_count import XorEquation, count_pure_xor, solve_xor_system, xor_chain_example
from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count


def test_xor_chain_rank_and_count():
    eqs, n = xor_chain_example()
    report = solve_xor_system(eqs, n)
    assert report.consistent
    assert report.rank == 2
    assert report.solution_count == 2
    assert count_pure_xor(eqs, n) == 2


def test_inconsistent_xor_system():
    eqs = (XorEquation((1,), 0), XorEquation((1,), 1))
    assert solve_xor_system(eqs, 1).solution_count == 0


def test_pure_xor_pipeline_without_cnf_clauses():
    eqs, n = xor_chain_example()
    cnf = CNF.from_lists(n, [])
    out = structure_aware_count(cnf, xor_equations=eqs, preprocess=False, timeout_s=5)
    assert out['engine'] == 'GF2_XOR_ELIMINATION'
    assert out['count'] == '2'

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.gf2_xor_count import XorEquation
from veritas.solvers.external_baselines import compare_count_baselines


def test_compare_matches_exhaustive_without_ganak(tmp_path):
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    row = compare_count_baselines(cnf, structure_aware_count, timeout_s=5, preprocess=True)
    assert row['exhaustive_count'] == 9
    assert row['internal_count'] == 9
    assert row['all_match'] is True
    assert row['parity_basis'] == 'pure_cnf'


def test_compare_mixed_xor_uses_encoded_parity():
    cnf = CNF.from_lists(3, [[1, 3]])
    eqs = (XorEquation((1, 2), 1),)
    row = compare_count_baselines(
        cnf,
        structure_aware_count,
        xor_equations=eqs,
        preprocess=False,
        xor_strategy='encode',
        timeout_s=5,
    )
    assert row['parity_basis'] == 'mixed_xor'
    assert row['internal_count'] == 3
    assert row['exhaustive_mixed_count'] == 3
    assert row['exhaustive_encoded_count'] == 3
    assert row['all_match'] is True

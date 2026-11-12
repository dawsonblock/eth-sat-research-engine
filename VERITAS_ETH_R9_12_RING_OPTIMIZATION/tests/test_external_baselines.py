from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.solvers.external_baselines import compare_count_baselines


def test_compare_matches_exhaustive_without_ganak(tmp_path):
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    row = compare_count_baselines(cnf, structure_aware_count, timeout_s=5, preprocess=True)
    assert row['exhaustive_count'] == 9
    assert row['internal_count'] == 9
    assert row['all_match'] is True

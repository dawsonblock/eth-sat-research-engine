from veritas.core.cnf import CNF
from veritas.research.cnf_structure import analyze_cnf_structure, structure_aware_count
from veritas.solvers.reference import exhaustive_count


def test_two_component_product_matches_exhaustive():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    report = analyze_cnf_structure(cnf)
    assert report.component_count == 2
    assert exhaustive_count(cnf) == 9
    result = structure_aware_count(cnf, timeout_s=5, verify_direct=True)
    assert result['structure']['decomposed'] is True
    assert result['count'] == '9'
    assert result['independent_count_checked'] is True


def test_unconstrained_variables_multiplier():
    cnf = CNF.from_lists(3, [[1, 2]])
    report = analyze_cnf_structure(cnf)
    assert report.global_unconstrained == 1
    assert exhaustive_count(cnf) == 6
    result = structure_aware_count(cnf, timeout_s=5)
    assert result['count'] == '6'

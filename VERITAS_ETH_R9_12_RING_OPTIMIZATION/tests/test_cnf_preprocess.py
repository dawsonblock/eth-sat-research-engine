from veritas.core.cnf import CNF
from veritas.research.cnf_preprocess import count_preserving_preprocess
from veritas.research.cnf_structure import structure_aware_count
from veritas.solvers.reference import exhaustive_count


def test_unit_propagation_preserves_count():
    cnf = CNF.from_lists(3, [[1], [1, 2], [-1, 3]])
    simplified, report = count_preserving_preprocess(cnf)
    assert report.unit_propagations == 2
    assert report.fixed_assignments == ((1, True), (3, True))
    assert exhaustive_count(cnf) == exhaustive_count(simplified)


def test_empty_clause_detected():
    _, report = count_preserving_preprocess(CNF.from_lists(2, [[1], [-1]]))
    assert report.empty_clause


def test_preprocess_before_structure_matches_exhaustive():
    cnf = CNF.from_lists(4, [[1], [1, 2], [3, 4]])
    assert structure_aware_count(cnf, preprocess=True, timeout_s=5)['count'] == str(exhaustive_count(cnf))

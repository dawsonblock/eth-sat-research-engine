from veritas.core.cnf import CNF
from veritas.research.hybrid_router import estimate_backends, hybrid_count


def test_two_component_formula_prefers_boundary_estimate():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    estimates = estimate_backends(cnf)
    names = {e.name for e in estimates}
    assert 'EXACT_BOUNDARY_DP' in names
    assert 'EXACT_VARIABLE_ELIMINATION' in names
    result = hybrid_count(cnf, timeout_s=5)
    assert 'routing' in result
    assert result['routing']['chosen_backend'] in names
    assert result['count'] == '9'


def test_routing_carries_no_complexity_claim():
    cnf = CNF.from_lists(3, [[1, 2], [-1, 2]])
    result = hybrid_count(cnf, timeout_s=5)
    assert 'subexponential' in result['routing']['warning']

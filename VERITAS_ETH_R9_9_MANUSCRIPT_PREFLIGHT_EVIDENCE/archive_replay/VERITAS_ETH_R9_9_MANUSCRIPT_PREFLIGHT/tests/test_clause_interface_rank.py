import pytest

from veritas.research.clause_interface_rank import audit_clause_interface_rank


@pytest.mark.parametrize('crossings', range(7))
def test_exact_compatibility_ranks_over_two_fields(crossings):
    result = audit_clause_interface_rank(crossings)
    assert result['dimension'] == 1 << crossings
    assert result['rational_rank'] == result['dimension']
    assert result['binary_rank'] == result['dimension']
    assert not result['universal_sat_lower_bound_proven']


def test_rank_audit_enforces_explicit_matrix_budget():
    with pytest.raises(ValueError, match='budget'):
        audit_clause_interface_rank(6, max_entries=4095)
    with pytest.raises(ValueError, match='0..6'):
        audit_clause_interface_rank(7)

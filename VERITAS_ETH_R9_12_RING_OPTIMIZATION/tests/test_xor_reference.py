from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation
from veritas.research.gf2_xor_mixed import reference_mixed_count


def test_reference_independent_small_n():
    cnf = CNF.from_lists(3, [[1, 3]])
    eqs = (XorEquation((1, 2), 1),)
    ref = reference_mixed_count(cnf, eqs)
    assert ref.independent and ref.count == 3


def test_reference_not_independent_large_active_support():
    n = 20
    cnf = CNF.from_lists(n, [list(range(1, n + 1))])
    eqs = tuple(XorEquation((i, i + 1), 0) for i in range(1, n))
    ref = reference_mixed_count(cnf, eqs, exhaustive_max_active=18)
    assert not ref.independent and ref.count is None


def test_active_support_reference():
    cnf = CNF.from_lists(22, [[1, 2]])
    eqs = (XorEquation((1, 2), 1),)
    ref = reference_mixed_count(cnf, eqs, exhaustive_max_active=18)
    assert ref.independent and ref.count == 2

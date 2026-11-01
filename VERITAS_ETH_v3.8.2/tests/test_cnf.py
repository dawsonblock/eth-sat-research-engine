import pytest
from veritas.core.cnf import CNF


def test_dimacs_roundtrip():
    for cnf in [CNF.from_lists(3, [[1,-2],[3],[]]), CNF.from_lists(0, []), CNF.from_lists(1, [[]]), CNF.from_lists(7, [])]:
        assert CNF.from_dimacs(cnf.to_dimacs()) == cnf

@pytest.mark.parametrize('text',["1 0", "p cnf 1 2\n1 0", "p cnf 1 1\n2 0", "p cnf 1 1\n1", "p cnf 1 1\na 0", "p cnf 1 1\n1 0\n2 0", "p cnf -2 0", "p cnf 1 0\np cnf 1 0"])
def test_bad_dimacs(text):
    with pytest.raises(ValueError): CNF.from_dimacs(text)


def test_boolean_model_validation():
    cnf = CNF.from_lists(2, [[1, -2]])
    assert cnf.evaluate({1:True, 2:True})
    assert not cnf.evaluate({1:False, 2:True})
    with pytest.raises(ValueError): cnf.evaluate({1:True})
    with pytest.raises(ValueError): CNF.from_lists(1, [[True]])

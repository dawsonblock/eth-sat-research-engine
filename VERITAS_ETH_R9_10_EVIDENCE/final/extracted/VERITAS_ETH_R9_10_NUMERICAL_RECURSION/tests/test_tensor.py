import random
import pytest
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.tensor import from_cnf, brute_contract, eliminate


def test_edge_cases():
    for cnf in [CNF.from_lists(0,[]), CNF.from_lists(2, []), CNF.from_lists(2,[[]]), CNF.from_lists(2,[[1,-1]]), CNF.from_lists(3,[[1,1,-2],[-1,3]])]:
        network = from_cnf(cnf)
        expected = exhaustive_count(cnf)
        assert brute_contract(network) == expected
        assert eliminate(network) == expected
        assert eliminate(network, modulus=1 << (cnf.n+1)) == expected


def test_random_tensor_equivalence():
    rng = random.Random(1337)
    for _ in range(500):
        n = rng.randint(0,5)
        clauses = []
        for j in range(rng.randint(0,5)):
            k = rng.randint(0,3) if n else 0
            clauses.append([rng.choice((-1,1))*rng.randint(1,n) for i in range(k)])
        cnf = CNF.from_lists(n, clauses)
        network = from_cnf(cnf)
        expected = exhaustive_count(cnf)
        if network.edges <= 17:
            assert brute_contract(network) == expected
        assert eliminate(network) == expected


def test_tensor_cap():
    cnf = CNF.from_lists(2, [[1,2],[1,-2]])
    with pytest.raises(ValueError): eliminate(from_cnf(cnf), max_table_entries=1)

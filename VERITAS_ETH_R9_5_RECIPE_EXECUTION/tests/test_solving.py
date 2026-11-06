import random
from veritas.core.cnf import CNF
from veritas.solvers.reference import solve, exhaustive_count


def test_known():
    for cnf, expected in [(CNF.from_lists(0, []),1), (CNF.from_lists(1, [[]]),0), (CNF.from_lists(2, [[1]]),2), (CNF.from_lists(3, [[1,2]]),6), (CNF.from_lists(1, [[1],[-1]]),0), (CNF.from_lists(3, [[1,-1]]),8)]:
        assert solve(cnf, count=True).count == expected
        sat = solve(cnf)
        assert (sat.status == 'SAT') == bool(expected)
        if sat.status == 'SAT': assert cnf.evaluate(sat.model)


def test_random_diff():
    rng = random.Random(20261029)
    for _ in range(1250):
        n = rng.randrange(0,8)
        clauses = []
        for __ in range(rng.randrange(0,13)):
            if n == 0: clauses.append([])
            else: clauses.append([rng.choice([-1,1]) * rng.randint(1,n) for ___ in range(rng.randrange(0,6))])
        cnf = CNF.from_lists(n, clauses)
        expected = exhaustive_count(cnf)
        result = solve(cnf, count=True, timeout_s=4)
        assert result.status == 'COUNT' and result.count == expected, (cnf, result)
        witness = solve(cnf)
        assert witness.status in ('SAT','UNSAT')
        if expected: assert witness.status == 'SAT' and cnf.evaluate(witness.model)
        else: assert witness.status == 'UNSAT'


def test_budget_yields_unknown():
    cnf = CNF.from_lists(12, [[i, i+1] for i in range(1,12)])
    result = solve(cnf, count=True, max_nodes=1)
    assert result.status == 'UNKNOWN' and result.count is None

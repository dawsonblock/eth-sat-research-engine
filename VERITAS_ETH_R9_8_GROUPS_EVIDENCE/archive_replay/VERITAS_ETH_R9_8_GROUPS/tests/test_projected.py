import itertools
import random
from veritas.core.cnf import CNF
from veritas.solvers.projected import projected_count


def oracle(cnf, projected):
    solutions = set()
    for assignment in itertools.product([False,True], repeat=cnf.n):
        model = {i+1:b for i,b in enumerate(assignment)}
        if cnf.evaluate(model):
            solutions.add(tuple(model[v] for v in projected))
    return len(solutions)


def test_projection_examples():
    cnf = CNF.from_lists(3, [[1,2]])
    assert projected_count(cnf, [1]).count == 2
    assert projected_count(cnf, [2,1]).count == 3
    assert projected_count(cnf, []).count == 1
    assert projected_count(CNF.from_lists(3,[[1],[-1]]), []).count == 0
    assert projected_count(CNF.from_lists(0,[]), []).count == 1
    assert projected_count(CNF.from_lists(0,[[]]), []).count == 0


def test_projection_random():
    rng = random.Random(20261031)
    for _ in range(350):
        n = rng.randrange(0,8)
        cnf = CNF.from_lists(n, [[rng.choice((1,-1))*rng.randint(1,n) for _ in range(rng.randrange(0,4))] if n else []
                                 for __ in range(rng.randrange(0,9))])
        proj = rng.sample(list(range(1,n+1)), rng.randrange(0,n+1))
        out = projected_count(cnf,proj,timeout_s=4)
        assert out.status == 'COUNT'
        assert out.count == oracle(cnf,proj)


def test_projection_rejects_invalid():
    cnf = CNF.from_lists(3,[])
    for bad in [[1,1],[0],[4],[True],['1']]:
        try: projected_count(cnf,bad)
        except ValueError: pass
        else: assert False, f'accepted {bad}'
    assert projected_count(cnf,[1,2,3],max_nodes=1).status == 'UNKNOWN'


def test_projection_near_clause_cap_fails_closed():
    cnf = CNF.from_lists(1, [[1]] * 20000)
    res = projected_count(cnf,[1],timeout_s=2)
    assert res.status == 'UNKNOWN' and res.count is None

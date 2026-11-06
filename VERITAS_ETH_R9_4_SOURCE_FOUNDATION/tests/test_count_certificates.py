import copy
import random
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.solvers.count_certificates import make_count_certificate, check_count_certificate


def test_certified_counts():
    examples = [CNF.from_lists(0, []), CNF.from_lists(0, [[]]),
                CNF.from_lists(4, []), CNF.from_lists(2, [[1],[-1]]),
                CNF.from_lists(3, [[1,2], [-2,3]]),
                CNF.from_lists(3, [[1,-1]]),
                CNF.from_lists(3, [[1,1], [-2,2]]),
                CNF.from_lists(2, [[1,-1], [2,-2]])]
    for cnf in examples:
        built = make_count_certificate(cnf)
        assert built.status == 'COUNT'
        valid, reason, count, nodes = check_count_certificate(cnf, built.certificate)
        assert valid, reason
        assert count == built.count == exhaustive_count(cnf)
        assert nodes == built.nodes


def test_random_certified_counts():
    rng = random.Random(6940)
    for _ in range(360):
        n = rng.randint(0,6)
        clauses = [[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(0,3))] if n else []
                   for _ in range(rng.randint(0,7))]
        cnf = CNF.from_lists(n, clauses)
        made = make_count_certificate(cnf)
        assert made.status == 'COUNT'
        checked = check_count_certificate(cnf, made.certificate)
        assert checked[0], checked
        assert checked[2] == exhaustive_count(cnf)


def test_adversarial_mutations():
    cnf = CNF.from_lists(2, [[1,2]])
    built = make_count_certificate(cnf)
    assert built.status == 'COUNT'
    cases = []
    tamper = copy.deepcopy(built.certificate); tamper['count'] = '999'; cases.append(tamper)
    tamper = copy.deepcopy(built.certificate); tamper['cnf_sha256'] = '0'*64; cases.append(tamper)
    tamper = copy.deepcopy(built.certificate); tamper['root']['count'] = '2'; cases.append(tamper)
    tamper = copy.deepcopy(built.certificate); tamper['root'].pop('false', None); cases.append(tamper)
    tamper = copy.deepcopy(built.certificate); tamper['root'] = {'satisfied':True,'count':'4'}; cases.append(tamper)
    tamper = copy.deepcopy(built.certificate); tamper['root'] = {'split':1,'false':{'conflict':0,'count':'0'},'true':{'conflict':0,'count':'0'},'count':'0'};cases.append(tamper)
    for case in cases:
        assert not check_count_certificate(cnf, case)[0]
    assert not check_count_certificate(CNF.from_lists(2, [[1]]), built.certificate)[0]


def test_resource_limit_fails_closed():
    cnf = CNF.from_lists(6, [[1,2,3],[4,5,6]])
    built = make_count_certificate(cnf,max_nodes=1)
    assert built.status == 'UNKNOWN' and built.certificate is None

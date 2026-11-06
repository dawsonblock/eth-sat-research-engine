"""Adversarial checker tests: generated proofs and deliberate tampering."""
from copy import deepcopy
import random
from veritas.core.cnf import CNF
from veritas.solvers.certificates import make_unsat_certificate, check_unsat_certificate
from veritas.solvers.reference import exhaustive_count


def test_small_unsat_proofs():
    cases = [CNF.from_lists(0,[[]]), CNF.from_lists(1,[[1],[-1]]),
             CNF.from_lists(3,[[1,2],[-1],[-2]]),
             CNF.from_lists(2,[[1,2],[1,-2],[-1,2],[-1,-2]])]
    for cnf in cases:
        proof = make_unsat_certificate(cnf)
        assert proof.status == 'UNSAT'
        ok, _, steps = check_unsat_certificate(cnf, proof.certificate)
        assert ok and steps >= 1


def test_generated_proofs_fuzz():
    rng = random.Random(20261030)
    proofs = 0
    for _ in range(400):
        n = rng.randrange(0, 7)
        clauses = [[rng.choice([-1, 1])*rng.randint(1,n) for _ in range(rng.randrange(0,5))] if n else []
                   for __ in range(rng.randrange(0,11))]
        cnf = CNF.from_lists(n, clauses)
        built = make_unsat_certificate(cnf)
        assert built.status in ('SAT','UNSAT')
        if built.status == 'UNSAT':
            proofs += 1
            assert exhaustive_count(cnf) == 0
            assert check_unsat_certificate(cnf, built.certificate)[0]
        else:
            assert cnf.evaluate(built.model)
            assert exhaustive_count(cnf) > 0
    assert proofs > 100


def test_adversarial_tamper():
    cnf = CNF.from_lists(2, [[1,2], [1,-2], [-1,2], [-1,-2]])
    proof = make_unsat_certificate(cnf).certificate
    assert check_unsat_certificate(cnf,proof)[0]
    bad = deepcopy(proof)
    bad['cnf_sha256'] = '0'*64
    assert not check_unsat_certificate(cnf,bad)[0]
    bad = deepcopy(proof)
    bad['root'] = {'conflict':0}
    assert not check_unsat_certificate(cnf,bad)[0]
    bad = deepcopy(proof)
    bad['root'] = {'unit':1,'clause':0,'next':{'conflict':0}}
    assert not check_unsat_certificate(cnf,bad)[0]
    bad = deepcopy(proof)
    bad['root'] = {'split':1,'false':{'conflict':0},'true':{'conflict':0}}
    assert not check_unsat_certificate(cnf,bad)[0]
    bad = deepcopy(proof)
    bad['root']['extra'] = 'unrecognized'
    assert not check_unsat_certificate(cnf,bad)[0]
    assert not check_unsat_certificate(cnf, ['not a cert'])[0]
    assert not check_unsat_certificate(cnf, proof, max_nodes=1)[0]
    assert not check_unsat_certificate(CNF.from_lists(2, []), proof)[0]


def test_sat_cannot_have_valid_unsat_certificate():
    sat = CNF.from_lists(4, [[1,2]])
    # Any attempted 'proof' with empty clause references must fail the checker.
    fake = {'format':'veritas-dpll-refutation-v1','cnf_sha256':sat.digest(),'root':{'conflict':0}}
    assert not check_unsat_certificate(sat,fake)[0]
    built = make_unsat_certificate(sat)
    assert built.status == 'SAT' and sat.evaluate(built.model)


def test_budget_fails_closed():
    # Full contradictory 3-variable cube has no unit clauses at root.
    cnf = CNF.from_lists(3, [[a,b,c] for a in (1,-1) for b in (2,-2) for c in (3,-3)])
    out = make_unsat_certificate(cnf, max_nodes=1)
    assert out.status == 'UNKNOWN' and out.certificate is None

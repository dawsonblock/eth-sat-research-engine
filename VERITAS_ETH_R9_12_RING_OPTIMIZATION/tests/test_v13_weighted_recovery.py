"""Independent cross-backend checks for the new end-to-end reconstruction."""
from dataclasses import replace
import random
import pytest

from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.weighted_recovery import (
    recover_weighted_count, verify_recovery_transcript, RecoveryBudgetExceeded,
)


@pytest.mark.parametrize('n,clauses',[
    (0,[]), (1,[]), (2,[]), (1,[[1]]), (1,[[1],[-1]]),
    (2,[[1,2]]), (2,[[1,2],[-2]]), (3,[[1,-1],[2,3]]),
    (4,[[1,2],[2,-3]]), (3,[[1,1],[2,2],[-3]]),
    (4,[[]]), (2,[[1,-1]]), (3,[[1,2],[-2,3]])
])
def test_recovery_count_and_transcript(n,clauses):
    cnf=CNF.from_lists(n,clauses)
    for L in (1,2):
        for span in (1,L):
            res=recover_weighted_count(cnf,packet_size=L,group_span=span)
            assert res.exact_count==exhaustive_count(cnf,max_vars=12)
            assert res.residue==res.exact_count
            assert res.data_bits==res.target_bits+res.guard_bits
            assert res.independent_jet_checked and res.independent_count_checked
            assert verify_recovery_transcript(cnf,res,replay_jets=True)
            assert len(res.transcript_sha256)==64


def test_residue_not_confused_with_exact():
    cnf=CNF.from_lists(4,[])
    res=recover_weighted_count(cnf,precision_bits=2)
    assert res.exact_count is None and res.residue==0
    assert verify_recovery_transcript(cnf,res,replay_jets=True)


def test_transcript_tampering_and_limits_fail_closed():
    cnf=CNF.from_lists(2,[[1,2],[-2]])
    res=recover_weighted_count(cnf)
    assert not verify_recovery_transcript(cnf,replace(res,residue=res.residue+1))
    assert not verify_recovery_transcript(cnf,replace(res,transcript_sha256='0'*64))
    broken=list(list(x) for x in res.node_jets)
    broken[0][0]^=1
    assert not verify_recovery_transcript(cnf,replace(res,node_jets=tuple(map(tuple,broken))))
    with pytest.raises(RecoveryBudgetExceeded):
        recover_weighted_count(cnf,max_work_assignments=1)
    with pytest.raises(ValueError):
        recover_weighted_count(cnf,max_edges=1)
    with pytest.raises(ValueError):
        recover_weighted_count(cnf,packet_size=4)
    with pytest.raises(ValueError):
        recover_weighted_count(cnf,group_span=3)
    with pytest.raises(ValueError):
        recover_weighted_count(cnf,precision_bits=0)


def test_randomized_differential():
    rng=random.Random(130026)
    for i in range(100):
        n=rng.randrange(1,5)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            clause=[rng.choice((-1,1))*rng.randrange(1,n+1) for _ in range(rng.randrange(0,3))]
            if sum(map(len,clauses))+len(clause)>5: break
            clauses.append(clause)
        cnf=CNF.from_lists(n,clauses)
        result=recover_weighted_count(cnf,packet_size=2,group_span=1,
                                       cross_check=i%3 != 0)
        assert result.exact_count==exhaustive_count(cnf,max_vars=12)
        assert verify_recovery_transcript(cnf,result,replay_jets=(i%10==0))

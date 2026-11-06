import copy
from itertools import product
import random
import pytest
from veritas.research.eth_packing_v26 import construct_d3_packing,verify_d3_packing
from veritas.research.eth_packing_v26.expectation import (assign_full_d3_labels,expected_sq_load_scaled,
                                                            PackingBudgetExceeded)
from veritas.research.eth_packing.parameters import manuscript_parameters


def test_published_manuscript_floor_parameters():
    assert manuscript_parameters(1000).u==0
    assert manuscript_parameters(1000).a==0
    assert not manuscript_parameters(1000).eligible
    assert manuscript_parameters(1<<131072,depth=1).u==0
    with pytest.raises(ValueError):manuscript_parameters(1000,M=10)
    assert not manuscript_parameters(1000,M=1000,delta=4).eligible


def _brute_expectation(edges,partial,r,a):
    keys=[(side,v,d) for side in ('R','C')
          for v in sorted({e[0] for e in edges} if side=='R' else {e[1] for e in edges})
          for d in range(a) if (side,v,d) not in partial]
    total=0;count=0
    for choices in product(range(r),repeat=len(keys)):
        labels=dict(partial);labels.update(zip(keys,choices))
        buckets={}
        for u,v in edges:
            k=(tuple(labels[('R',u,d)] for d in range(a)),
               tuple(labels[('C',v,d)] for d in range(a)))
            buckets[k]=buckets.get(k,0)+1
        total+=sum(n*n for n in buckets.values());count+=1
    return total, count


def test_conditional_expectation_matches_brute_random():
    rng=random.Random(2610)
    for _ in range(45):
        edges=[(rng.randrange(2),rng.randrange(2)) for _ in range(rng.randrange(1,6))]
        partial={}
        for side in ('R','C'):
            for v in range(2):
                if rng.random()<.35:partial[(side,v,0)]=rng.randrange(2)
        D=4
        brute,cases=_brute_expectation(edges,partial,2,1)
        got=expected_sq_load_scaled(edges,partial,2,1)
        assert got*cases==brute*D


def test_d3_exact_trace_and_independent_check():
    edges=[(i%5,(i*i+3)%7) for i in range(25)]
    c=construct_d3_packing(edges,r=2,a=1)
    check=verify_d3_packing(c)
    assert check['valid'] and check['conditional_expectation_nonincreasing']
    assert check['packet_count']==c['D']*c['H_pad']//c['L']
    assert c['final_square_scaled']<=c['initial_expected_square_scaled']
    assert not check['d6_numeric_preconditions_satisfied']


def test_multicoordinate_collision_packing():
    edges=[(i%6,(3*i+i//6)%7) for i in range(16)]
    cert=construct_d3_packing(edges,r=2,a=2)
    assert verify_d3_packing(cert)['valid']
    assert cert['L']==4 and cert['D']==16


def test_scoped_d3_numerical_preconditions_are_really_satisfied():
    # 32 vertices per side, degree exactly four, M=128; r=2,a=1, D=4.
    # M >= 2 D^2 Delta = 128, M >= LD = 8 and 2L <= Delta = 4.
    edges=[(u,(u+t)%32) for u in range(32) for t in range(4)]
    c=construct_d3_packing(edges,r=2,a=1,max_work=5_000_000,
                           require_theorem_preconditions=True)
    report=verify_d3_packing(c)
    assert report['valid'] and report['d6_numeric_preconditions_satisfied']
    assert report['finite_bounds_satisfied']
    assert report['potential_bound']
    assert report['status']=='D3_FINITE_BOUNDS_CERTIFIED'


def test_tamper_rejected():
    edges=[(i%4,(i+2)%5) for i in range(13)]
    cert=construct_d3_packing(edges,r=2,a=2)
    for mutate in ('drop_packet','duplicate_wire','change_label','inflate_pad','change_potential','change_trace'):
        bad=copy.deepcopy(cert)
        if mutate=='drop_packet':bad['packets'].pop()
        if mutate=='duplicate_wire':
            slots=[(p,i) for p in bad['packets'] for i,e in enumerate(p['slots']) if e is not None]
            # Duplication even if slot orientation happens to be incompatible.
            if len(slots)>=2:slots[0][0]['slots'][slots[0][1]]=slots[1][0]['slots'][slots[1][1]]
        if mutate=='change_label':bad['row_labels']['0'][0]^=1
        if mutate=='inflate_pad':bad['H_pad']+=4
        if mutate=='change_potential':bad['final_square_scaled']+=1
        if mutate=='change_trace':bad['conditional_expectation_steps'][0]['expected_square_scaled']+=1
        assert not verify_d3_packing(bad)['valid'],mutate


def test_fail_closed_preconditions_and_budget():
    with pytest.raises(ValueError):construct_d3_packing([(0,1)],r=2,a=1,require_theorem_preconditions=True)
    with pytest.raises(PackingBudgetExceeded):construct_d3_packing([(0,1)]*10,r=2,a=1,max_work=1)
    with pytest.raises(PackingBudgetExceeded):construct_d3_packing([(0,1)],r=64,a=3)


def test_side_specific_labels_even_for_equal_numeric_ids():
    c=construct_d3_packing([(0,0),(0,1),(1,0),(1,1)],r=2,a=1)
    assert '0' in c['row_labels'] and '0' in c['column_labels']
    assert verify_d3_packing(c)['valid']

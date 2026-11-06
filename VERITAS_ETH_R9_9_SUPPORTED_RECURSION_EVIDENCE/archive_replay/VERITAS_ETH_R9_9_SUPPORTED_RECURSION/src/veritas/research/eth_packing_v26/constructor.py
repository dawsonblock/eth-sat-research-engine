"""Uniform padded directed-pair classes and full packet-slot orientation.

This is the packet embedding of `lem:tensor-packets` in `app:tensor` (historical
alias "D.3"), not the smaller ad hoc bucket scheme from v2.5. Every directed label class is padded to the *same* H, divisible by L,
including empty classes. Each unordered class receives 2**a' orientations and
L/2**a' copies, hence H*2**a'/L complete packets.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from itertools import product
from .expectation import (assign_full_d3_labels,validate_edges,max_side_degree,
                          PackingBudgetExceeded)


def d3_preconditions(M,r,a,delta):
    if any(type(v) is not int for v in (M,r,a,delta)) or M<0 or r<2 or a<1 or delta<0:
        raise ValueError('invalid parameters')
    L=1<<a
    D=r**(2*a)
    return {'M_ge_2_D_squared_delta':M>=2*D*D*delta,
            'M_ge_LD':M>=L*D,
            '2L_le_delta':2*L<=delta,
            'D':D,'L':L, 'delta':delta}


def construct_d3_packing(edges,*,r=2,a=1,max_work=3_000_000,
                         max_packets=10000,require_theorem_preconditions=False, _budget=None):
    if _budget is not None: _budget.tick()
    edges=validate_edges(edges)
    if len(edges)>4000 or type(a) is not int or not 1<=a<=5 or type(r) is not int or not 2<=r<=64:
        raise ValueError('unsupported input size or radix/dimension')
    M=len(edges);L=1<<a;D=r**(2*a)
    if D>4096:
        raise PackingBudgetExceeded('label-class expansion exceeds 4096 classes')
    delta=max_side_degree(edges)
    hypotheses=d3_preconditions(M,r,a,delta)
    if require_theorem_preconditions and not all(hypotheses[k] for k in ('M_ge_2_D_squared_delta','M_ge_LD','2L_le_delta')):
        raise ValueError('D.6 preconditions do not hold on input with observed maximum degree')
    labels=assign_full_d3_labels(edges,r=r,a=a,max_work=max_work,_budget=_budget)
    rows,cols=labels['rows'],labels['columns']
    classes=defaultdict(list)
    for eid,(u,v) in enumerate(edges):
        classes[(tuple(rows[str(u)]),tuple(cols[str(v)]))].append(eid)
    maximum=max(map(len,classes.values()),default=0)
    H=((maximum+L-1)//L)*L
    if D*H//L>max_packets:
        raise PackingBudgetExceeded('padded packet count exceeds resource budget')
    # Uniform directed class population, including empty classes.
    empty=tuple([None]*H)
    padded={gamma:tuple(eids)+tuple([None]*(H-len(eids))) for gamma,eids in classes.items()}
    packets=[]
    for unordered in product(*[tuple((x,y) for x in range(r) for y in range(x,r)) for _ in range(a)]):
        if _budget is not None: _budget.tick()
        differing=[d for d,(x,y) in enumerate(unordered) if x!=y]
        equal=[d for d,(x,y) in enumerate(unordered) if x==y]
        copies=1<<len(equal)
        for j in range(H//copies):
            slots=[]
            for slot in range(L):
                if _budget is not None: _budget.tick()
                row=[];col=[]
                copy_index=0
                for k,d in enumerate(equal):
                    copy_index|=((slot>>d)&1)<<k
                for d,(x,y) in enumerate(unordered):
                    if x==y:
                        row.append(x);col.append(y)
                    elif (slot>>d)&1:
                        row.append(y);col.append(x)
                    else:
                        row.append(x);col.append(y)
                gamma=(tuple(row),tuple(col))
                slots.append(padded.get(gamma,empty)[j*copies+copy_index])
            packets.append({'symbol_pairs':[list(x) for x in unordered],'slots':slots})
    certificate={
        'schema':'VERITAS_ETH_D3_CERT_V1', 'claim':'FINITE_D3_PACKET_CONSTRUCTION',
        'r':r,'a':a,'L':L,'D':D,'M':M,'H_pad':H,'delta':delta,
        'edges':[list(x) for x in edges],
        'row_labels':rows,'column_labels':cols,'packets':packets,
        'initial_expected_square_scaled':labels['initial_expected_square_scaled'],
        'final_square_scaled':labels['final_square_scaled'],
        'hypotheses':hypotheses,
        'conditional_expectation_steps':labels['steps']
    }
    from .checker import verify_d3_packing
    result=verify_d3_packing(certificate,check_trace=True,_budget=_budget)
    if not result['valid']:
        raise AssertionError('internal D3 packing verifier rejected construction: '+str(result))
    certificate['verification']=result
    return certificate

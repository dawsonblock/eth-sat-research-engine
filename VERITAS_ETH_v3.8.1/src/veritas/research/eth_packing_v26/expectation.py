"""Exact deterministic conditional expectation for Appendix D.3's *directed pair-label* load.

The independent random variables are a symbol at each coordinate of each row- or
column-side vertex. Shared numeric IDs across sides do NOT share random variables.
For edges e,f, their directed label pairs coincide precisely when the row-side
labels agree AND the column-side labels agree. Each unforced equality contributes
probability 1/r, giving integral expected squared-load scores after multiplying
by D=r**(2*a).

This is a bounded executable version of the mathematical derandomization, not
an implementation of D.4.4 or a proof of subexponential complexity.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass


class PackingBudgetExceeded(ValueError):
    pass


def validate_edges(edges):
    if not isinstance(edges, (list,tuple)):
        raise ValueError('edges must be a sequence')
    result=[]
    for e in edges:
        if not isinstance(e,(list,tuple)) or len(e)!=2 or any(type(v) is not int or v<0 for v in e):
            raise ValueError('each edge must contain two nonnegative integer IDs')
        result.append((e[0],e[1]))
    return tuple(result)


def variables(edges):
    return tuple([('R',v) for v in sorted({u for u,_ in edges})] +
                 [('C',v) for v in sorted({v for _,v in edges})])


def max_side_degree(edges):
    return max([0]+list(Counter(('R',u) for u,_ in edges).values())+
               list(Counter(('C',v) for _,v in edges).values()))


def expected_sq_load_scaled(edges, assignments, r, a, _budget=None):
    """Returns D * E[sum_gamma X_gamma**2], an exact integer.

    assignments is a map of (side,vertex,coord) to an integer symbol.
    Unassigned coordinates are independent uniform labels on [r].
    """
    if type(r) is not int or r<2 or type(a) is not int or a<1:
        raise ValueError('invalid r or a')
    D=r**(2*a)
    M=len(edges)
    total=M*D   # diagonal edge pairs
    for i,(u,v) in enumerate(edges):
        for w,z in edges[:i]:
            if _budget is not None: _budget.tick()
            exponent=0
            contradicted=False
            for d in range(a):
                for side,left,right in (('R',u,w),('C',v,z)):
                    if left==right:
                        continue
                    x=assignments.get((side,left,d))
                    y=assignments.get((side,right,d))
                    if x is not None and y is not None and x!=y:
                        contradicted=True
                        break
                    if x is None or y is None:
                        exponent+=1
                if contradicted:
                    break
            if not contradicted:
                total += 2*(D // (r**exponent))
    return total


def assign_full_d3_labels(edges, *, r=2, a=1, max_work=3_000_000, _budget=None):
    """Assign labels coordinatewise by exact conditional expectation.

    At every step the chosen candidate minimizes the *conditional expected* sum
    of squared directed pair-class loads, so the unnormalized potential cannot
    increase. This is deterministic and mathematically equivalent to fixing
    whole r-ary label vectors one at a time.
    """
    edges=validate_edges(edges)
    if type(r) is not int or type(a) is not int or not (2<=r<=64 and 1<=a<=8):
        raise ValueError('unsupported radix or dimension')
    vs=variables(edges)
    estimated_work=(len(vs)*a*r+1)*len(edges)*max(1,len(edges))*a
    if type(max_work) is not int or max_work<1 or estimated_work>max_work:
        raise PackingBudgetExceeded(f'conditional expectation estimated work {estimated_work} exceeds {max_work}')
    assignments={}
    D=r**(2*a)
    initial=expected_sq_load_scaled(edges,assignments,r,a,_budget)
    before=initial
    steps=[]
    # Choosing higher-degree vertices first tends to improve practical local scores.
    degrees=Counter(('R',u) for u,_ in edges)+Counter(('C',v) for _,v in edges)
    for side,v in sorted(vs,key=lambda k:(-degrees[k],k)):
        for d in range(a):
            best=None
            for value in range(r):
                if _budget is not None: _budget.tick()
                assignments[(side,v,d)]=value
                score=expected_sq_load_scaled(edges,assignments,r,a,_budget)
                cand=(score,value)
                if best is None or cand<best:
                    best=cand
            assert best is not None
            score,value=best
            assignments[(side,v,d)]=value
            if score>before:
                raise AssertionError('conditional expectation increased')
            steps.append({'side':side,'vertex':v,'coordinate':d,'symbol':value,
                          'expected_square_scaled':score})
            before=score
    row={str(v):[assignments[('R',v,d)] for d in range(a)] for side,v in vs if side=='R'}
    col={str(v):[assignments[('C',v,d)] for d in range(a)] for side,v in vs if side=='C'}
    return {'rows':row,'columns':col,'steps':steps,
            'initial_expected_square_scaled':initial,
            'final_square_scaled':before,'D':D,
            'method':'EXACT_CONDITIONAL_EXPECTATION_DIRECTED_PAIR_LOAD'}

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


# The incremental labeler keeps one record per unordered edge pair plus
# endpoint-update lists, so its live table is O(M**2). This cap fails closed
# on that table size, matching the module's other explicit resource limits.
# Callers that need a larger table must raise it deliberately.
DEFAULT_MAX_PAIR_RECORDS = 250_000


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


def conditional_expectation_work_bound(edges, *, r: int, a: int) -> int:
    """Conservative operation estimate for the incremental D.3 derandomizer.

    Each unordered edge pair is stored once. Across both sides, it appears in
    at most four endpoint-update lists. Summing those list lengths over all
    vertices is therefore at most ``2*M*(M-1)``. The constructor scans those
    lists for each coordinate/candidate, commits one selected candidate per
    coordinate, and performs one final direct score replay. This gives an
    ``O(a*r*M**2)`` operation bound, with a deliberately loose constant.
    It is an operation estimate, not a bit-operation or wall-time theorem.
    """
    edges = validate_edges(edges)
    if type(r) is not int or type(a) is not int or not (2 <= r <= 64 and a >= 1):
        raise ValueError('unsupported radix or dimension')
    m = len(edges)
    if not m:
        return 0
    return (4 * r + 20) * a * m * m


def assign_full_d3_labels(edges, *, r=2, a=1, max_work=3_000_000, _budget=None,
                          max_pair_records=DEFAULT_MAX_PAIR_RECORDS):
    """Assign labels coordinatewise by exact conditional expectation.

    At every coordinate step the chosen candidate minimizes the *conditional
    expected* sum of squared directed pair-class loads, so the unnormalized
    potential cannot increase. This deterministic degree-first, coordinatewise
    algorithm preserves the same nonincrease invariant as whole-word
    conditional expectation, but can select different labels and traces from
    the sorted, whole-word streaming constructor.
    """
    edges=validate_edges(edges)
    if type(r) is not int or type(a) is not int or not (2<=r<=64 and a>=1):
        raise ValueError('unsupported radix or dimension')
    if max_work is not None and (type(max_work) is not int or max_work < 1):
        raise ValueError('max_work must be a positive integer or None')
    if type(max_pair_records) is not int or max_pair_records < 0:
        raise ValueError('max_pair_records must be a nonnegative integer')
    vs=variables(edges)
    estimated_work=conditional_expectation_work_bound(edges,r=r,a=a)
    if max_work is not None and estimated_work>max_work:
        raise PackingBudgetExceeded(f'conditional expectation estimated work {estimated_work} exceeds {max_work}')
    assignments={}
    D=r**(2*a)
    M=len(edges)
    pair_count=M*(M-1)//2
    if pair_count>max_pair_records:
        raise PackingBudgetExceeded(
            f'labeler pair table {pair_count} exceeds {max_pair_records} records')

    # Store each unordered edge pair's number of still-random equality tests,
    # whether an already-fixed comparison has contradicted equality, and its
    # exact contribution to D*E[sum_gamma X_gamma^2].  Assigning a label only
    # changes pairs incident to that vertex whose other endpoint is already
    # labelled. If the other endpoint is still random, the equality event has
    # probability 1/r for every candidate symbol and its contribution stays
    # unchanged. This avoids recomputing the whole M^2 score for every choice.
    pair_unknown=[]
    pair_conflicted=[]
    pair_contribution=[]
    updates={}
    score=M*D
    for i,(u,v) in enumerate(edges):
        for j,(w,z) in enumerate(edges[:i]):
            if _budget is not None:
                _budget.tick()
            pair_id=len(pair_unknown)
            unknown=a*(int(u != w)+int(v != z))
            contribution=2*(D//(r**unknown))
            pair_unknown.append(unknown)
            pair_conflicted.append(False)
            pair_contribution.append(contribution)
            score+=contribution
            if u != w:
                updates.setdefault(('R',u),[]).append((pair_id,('R',w)))
                updates.setdefault(('R',w),[]).append((pair_id,('R',u)))
            if v != z:
                updates.setdefault(('C',v),[]).append((pair_id,('C',z)))
                updates.setdefault(('C',z),[]).append((pair_id,('C',v)))

    initial=score
    before=initial
    steps=[]
    # Choosing higher-degree vertices first tends to improve practical local scores.
    degrees=Counter(('R',u) for u,_ in edges)+Counter(('C',v) for _,v in edges)
    for side,v in sorted(vs,key=lambda k:(-degrees[k],k)):
        for d in range(a):
            best=None
            for value in range(r):
                if _budget is not None:
                    _budget.tick()
                trial=score
                for pair_id,other_vertex in updates.get((side,v),()):
                    if _budget is not None:
                        _budget.tick()
                    other=(*other_vertex,d)
                    if other not in assignments or pair_conflicted[pair_id]:
                        continue
                    old=pair_contribution[pair_id]
                    new=(old*r if value==assignments[other] else 0)
                    trial+=new-old
                cand=(trial,value)
                if best is None or cand<best:
                    best=cand
            assert best is not None
            next_score,value=best
            if next_score>before:
                raise AssertionError('conditional expectation increased')
            for pair_id,other_vertex in updates.get((side,v),()):
                if _budget is not None:
                    _budget.tick()
                other=(*other_vertex,d)
                if other not in assignments or pair_conflicted[pair_id]:
                    continue
                old=pair_contribution[pair_id]
                if value==assignments[other]:
                    if pair_unknown[pair_id] < 1:
                        raise AssertionError('resolved pair equality was not marked unknown')
                    pair_unknown[pair_id]-=1
                    new=old*r
                else:
                    pair_conflicted[pair_id]=True
                    new=0
                pair_contribution[pair_id]=new
                score+=new-old
            assignments[(side,v,d)]=value
            if score != next_score:
                raise AssertionError('incremental conditional expectation disagrees with candidate score')
            steps.append({'side':side,'vertex':v,'coordinate':d,'symbol':value,
                          'expected_square_scaled':score})
            before=score
    for unknown,conflicted,contribution in zip(pair_unknown,pair_conflicted,
                                                pair_contribution):
        if (not conflicted and
                (unknown != 0 or contribution != 2*D)):
            raise AssertionError('fully assigned pair has an inconsistent final contribution')
        if conflicted and contribution != 0:
            raise AssertionError('conflicted pair has a nonzero contribution')
    # Keep the direct all-pairs implementation as a final internal check. This
    # is still deterministic exact arithmetic and catches update-list defects.
    replay=expected_sq_load_scaled(edges,assignments,r,a,_budget)
    if replay != score:
        raise AssertionError('incremental conditional expectation differs from direct score')
    row={str(v):[assignments[('R',v,d)] for d in range(a)] for side,v in vs if side=='R'}
    col={str(v):[assignments[('C',v,d)] for d in range(a)] for side,v in vs if side=='C'}
    return {'rows':row,'columns':col,'steps':steps,
            'initial_expected_square_scaled':initial,
            'final_square_scaled':before,'D':D,
            'method':'EXACT_CONDITIONAL_EXPECTATION_DIRECTED_PAIR_LOAD'}

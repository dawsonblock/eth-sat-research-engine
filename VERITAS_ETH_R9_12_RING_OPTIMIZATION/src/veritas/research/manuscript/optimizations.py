"""Exact finite counting optimizations; no source/complexity qualification.

The distinct-parity-row quotient preserves the ordered-list greedy minimum,
including first-occurrence tie order. Unused-variable factorization preserves
common-zero counts exactly. Neither optimization activates source recursion or
makes a polynomial-space/subexponential runtime claim. The original reference
count route remains available unchanged.
"""
from itertools import combinations
from math import comb

from . import hashes
from .parameters import natural
from .resources import Budget,Limits,ResourceLimit
from .sparse import normalize_system
from .sparse_query import common_zeros


POLICY='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR'


def _independent_components(scopes,budget):
    """Partition constraints by shared variables; never split a constraint."""
    parent={}
    def root(v):
        while parent[v]!=v:
            parent[v]=parent[parent[v]];v=parent[v]
        return v
    for scope in scopes:
        budget.tick(len(scope)+1)
        budget.items(len(parent)+sum(v not in parent for v in scope),'component variables')
        for v in scope:parent.setdefault(v,v)
        if scope:
            first=scope[0]
            for v in scope[1:]:parent[root(v)]=root(first)
    groups={}
    for index,scope in enumerate(scopes):
        budget.tick()
        if scope:groups.setdefault(root(scope[0]),[]).append(index)
    budget.items(len(scopes)+len(parent),'component partition')
    return tuple(tuple(indices) for indices in groups.values()),len(parent)


def _component_receipt(total,budget,sizes,unused,reused):
    return dict(status='PASS_EXACT_COUNT',count=total,
                route='EXACT_INDEPENDENT_COMPONENT_PRODUCT',
                component_variables=sizes,unused_variables=unused,
                reused_components=reused,ledger=budget.report(),
                source_qualified=False,complexity_proven=False,
                executable_refinement_proven=False)


def _factored_components(n,system,budget,limits):
    scopes=tuple(tuple(sorted({v for m in eq for v in m})) for eq in system)
    groups,active=_independent_components(scopes,budget)
    if len(groups)<2:return None
    budget.bits(n+1,'component count')
    total=1;cache={};sizes=[];reused=0
    for indices in groups:
        variables=sorted({v for i in indices for v in scopes[i]})
        mapping={v:j for j,v in enumerate(variables)};sizes.append(len(variables))
        reduced=tuple(tuple(frozenset(mapping[v] for v in m) for m in system[i]) for i in indices)
        budget.tick(sum(1+len(m) for eq in reduced for m in eq))
        if reduced in cache:
            value=cache[reduced];reused+=1
        else:
            receipt=common_zeros(len(variables),reduced,limits=limits,budget=budget)
            if receipt['status']!='PASS_EXACT_COUNT':return receipt
            value=receipt['count']
            budget.items(sum(len(key) for key in cache)+len(reduced),'component cache equations')
            cache[reduced]=value
        total*=value
        if total==0:break
    return _component_receipt(total << (n-active),budget,sizes,n-active,reused)


def distinct_parity_rows(m,P,budget):
    """Rows in order of their lexicographically first length-P preimage.

    Weight w requires at least w odd codes and is attainable iff w<=P. The
    first preimage is P-w zeros followed by increasing selected odd codes.
    Thus weight order then lexicographic subsets preserves first-minimum ties.
    """
    natural(m,'clause count',1);natural(P,'hash-list length')
    budget.bits(m,'parity row');budget.items(min(m,P),'selected parity coordinates')
    total=0
    for weight in range(min(m,P)+1):
        total+=comb(m,weight);budget.bits(total.bit_length(),'distinct candidate count')
        if budget.limits.max_work is not None and total>budget.limits.max_work-budget.work:
            raise ResourceLimit('distinct parity-row enumeration exceeds allowance')
    for weight in range(min(m,P)+1):
        for selected in combinations(range(m),weight):
            budget.tick();yield sum(1<<edge for edge in selected)


def common_zeros_factored(n,equations,*,limits=Limits(),budget=None,event_sink=None):
    """Count only the occurring variables, then restore the unused factor."""
    budget=Budget(limits) if budget is None else budget
    try:
        system=normalize_system(n,equations)
        budget.tick(sum(1+len(monomial) for eq in system for monomial in eq))
        active=sorted({v for eq in system for monomial in eq for v in monomial})
        budget.items(len(active),'active-variable map');budget.bits(n+1,'factored count')
        if event_sink is None and not any(eq==(frozenset(),) for eq in system):
            components=_factored_components(n,system,budget,limits)
            if components is not None:return components
        inner=None
        if not active:
            result=0 if any(eq for eq in system) else 1<<n
        else:
            if len(active)==n:return common_zeros(n,system,limits=limits,budget=budget,event_sink=event_sink)
            mapping={v:i for i,v in enumerate(active)}
            reduced=tuple(tuple(frozenset(mapping[v] for v in monomial) for monomial in eq) for eq in system)
            receipt=common_zeros(len(active),reduced,limits=limits,budget=budget,event_sink=event_sink)
            if receipt['status']!='PASS_EXACT_COUNT':return receipt
            result=receipt['count'] << (n-len(active))
            inner=receipt
        result_receipt=dict(status='PASS_EXACT_COUNT',count=result,route='EXACT_UNUSED_VARIABLE_FACTOR',
                    active_variables=len(active),unused_variables=n-len(active),ledger=budget.report(),
                    source_qualified=False,complexity_proven=False)
        if inner is not None:
            result_receipt['inner_route']=inner['route']
            for key in ('degree_admission_fallback_branches','largest_fallback_degree',
                        'source_degree_limit','fallback_policy'):
                if key in inner:result_receipt[key]=inner[key]
        return result_receipt
    except ResourceLimit as exc:
        return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),source_qualified=False)


def greedy_rows_distinct(n,clauses,A0,P,*,limits=Limits(),budget=None,hash_event_sink=None):
    """Same greedy trajectory, quotienting rows and reusing a zero fixed point.

    Scores depend only on the represented parity equation. Once the first
    minimum is zero, adding its trivial equation cannot change any later score.
    All required rows and trace values remain present.
    """
    natural(n,'declared variables',1)
    budget=Budget(limits) if budget is None else budget
    m=len(clauses);natural(m,'clause count',1);natural(P,'hash-list length')
    budget.items(len(A0)+3*n,'greedy parity rows')
    violation=[hashes.clause_violation_polynomial(c) for c in clauses];rows=list(A0)
    if hash_event_sink is not None:
        hash_event_sink(dict(kind='hash_start',n=n,clauses=[list(c) for c in clauses],P=P,initial_rows=list(A0)))
    for index in range(3*n):
        budget.tick();best_count=best_row=None;scores=[] if hash_event_sink is not None else None
        for word in distinct_parity_rows(m,P,budget):
            receipt=common_zeros_factored(n,hashes.system_equations(rows+[word],violation),limits=limits,budget=budget)
            if receipt['status']!='PASS_EXACT_COUNT':raise ResourceLimit('candidate count: '+str(receipt.get('reason',receipt['status'])))
            value=receipt['count']
            if scores is not None:
                budget.items(len(scores)+1,'candidate score trace');scores.append([word,value])
            if best_count is None or value<best_count:best_row,best_count=word,value
        frozen_scores=None
        if best_row==0:
            # Adding row zero appends a trivial equation. Every candidate score
            # and the first-minimum order are therefore unchanged thereafter.
            # Keep all 3n rows and every trace value; only repeated evaluation is
            # omitted. Guard the semantic dependency against future changes.
            budget.tick(m)
            if any(hashes.system_equations((0,),violation)):
                raise ArithmeticError('zero parity row is no longer a trivial equation')
            if scores is not None:
                budget.items(2*len(scores),'immutable hash score snapshot')
                frozen_scores=tuple(tuple(pair) for pair in scores)
        if hash_event_sink is not None:
            hash_event_sink(dict(kind='hash_round',index=index,scores=scores,selected=best_row,count=best_count))
        rows.append(best_row)
        if best_row==0:
            for later in range(index+1,3*n):
                budget.tick();budget.items(len(rows)+1,'zero fixed-point rows')
                rows.append(0)
                if hash_event_sink is not None:
                    budget.items(2*len(frozen_scores),'reused hash score trace')
                    hash_event_sink(dict(kind='hash_round',index=later,
                        scores=[list(pair) for pair in frozen_scores],selected=0,count=best_count))
            break
    return tuple(rows)


def count_sparse_formula_optimized(n,clauses,B,k_bound,*,limits=Limits(),budget=None,
                                   event_sink=None,hash_event_sink=None):
    budget=Budget(limits) if budget is None else budget
    try:
        if not clauses or any(not c for c in clauses):
            if not clauses:budget.bits(n+1,'trivial count')
            return dict(status='PASS_EXACT_COUNT',count=0 if clauses else 1<<n,
                        route='TRIVIAL_CNF',ledger=budget.report(),source_qualified=False)
        _,P,_=hashes.sparse_check_parameters(len(clauses),B,n)
        A0=hashes.sparse_checks(n,clauses,B,limits=limits,budget=budget)
        rows=greedy_rows_distinct(n,clauses,A0,P,limits=limits,budget=budget,hash_event_sink=hash_event_sink)
        violation=[hashes.clause_violation_polynomial(c) for c in clauses]
        receipt=common_zeros_factored(n,hashes.system_equations(rows,violation),limits=limits,budget=budget,event_sink=event_sink)
        if receipt['status']!='PASS_EXACT_COUNT':return receipt
        result=dict(status='PASS_EXACT_COUNT',count=receipt['count'],route='PARITY_CHECKS_SPARSE_QUERY',
                    ledger=budget.report(),source_qualified=False,complexity_proven=False)
        if receipt.get('degree_admission_fallback_branches'):
            result['final_query_degree_fallback']=dict(
                route=receipt.get('inner_route',receipt['route']),
                **{key:receipt[key] for key in ('degree_admission_fallback_branches',
                   'largest_fallback_degree','source_degree_limit','fallback_policy')})
        return result
    except ResourceLimit as exc:
        return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),source_qualified=False)


def count_optimized(formula,*,limits=Limits(),budget=None,event_sink=None,hash_event_sink=None):
    """General CNF dispatcher with exact distinct-row/support reductions.

    Accepts the same Formula inputs and budgets as the reference count API.
    General hard instances may still return INCONCLUSIVE_RESOURCE_LIMIT. A
    completed count is exact; it is not a source-active or asymptotic claim.
    """
    from .cnf import _count
    def counter(n,clauses,B,k_bound,**kwargs):
        return count_sparse_formula_optimized(n,clauses,B,k_bound,hash_event_sink=hash_event_sink,**kwargs)
    budget=Budget(limits) if budget is None else budget
    try:
        # Certificate-producing calls retain their historical trace and route.
        # Only the explicit optimized API factors disconnected CNF components.
        receipt=None
        if event_sink is None and hash_event_sink is None:
            from .cnf import Formula
            normalized=formula.normalize(budget)
            scopes=tuple(tuple(sorted({abs(v) for v in c})) for c in normalized.clauses)
            groups,active=_independent_components(scopes,budget)
            if () not in normalized.clauses and len(groups)>1:
                budget.bits(formula.n+1,'component model count')
                total=1;cache={};sizes=[];reused=0
                for indices in groups:
                    variables=sorted({v for i in indices for v in scopes[i]})
                    mapping={v:j+1 for j,v in enumerate(variables)};sizes.append(len(variables))
                    clauses=tuple(tuple(mapping[abs(v)]*(1 if v>0 else -1) for v in normalized.clauses[i]) for i in indices)
                    budget.tick(sum(len(c)+1 for c in clauses))
                    key=(len(variables),clauses)
                    if key in cache:value=cache[key];reused+=1
                    else:
                        part=_count(Formula(len(variables),clauses),limits=limits,budget=budget,sparse_counter=counter)
                        if part['status']!='PASS_EXACT_COUNT':
                            receipt=part;break
                        value=part['count']
                        budget.items(sum(len(k[1]) for k in cache)+len(clauses),'component cache clauses')
                        cache[key]=value
                    total*=value
                    if total==0:break
                if receipt is None:
                    receipt=_component_receipt(total << (formula.n-active),budget,sizes,formula.n-active,reused)
        if receipt is None:
            receipt=_count(formula,limits=limits,budget=budget,event_sink=event_sink,sparse_counter=counter)
    except ResourceLimit as exc:
        receipt=dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),source_qualified=False)
    return dict(receipt,optimization_policy=POLICY,executable_refinement_proven=False,complexity_proven=False)

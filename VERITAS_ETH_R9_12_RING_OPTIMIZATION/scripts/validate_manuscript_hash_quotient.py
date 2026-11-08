"""Exact finite optimization of greedy hash candidates, separate experiment.

The production greedy search enumerates ordered lists gamma in ([m]x{0,1})^P.
Its score depends only on the parity row they produce. All achievable rows have
weight <= P; each such row is achievable by its selected odd codes and zero
padding. Its first list is leading zeros followed by increasing selected codes,
so first-occurrence order is increasing weight then lexicographic subsets.

This driver temporarily substitutes an independently checked distinct-row
search and exact unused-variable factorization into the general CNF dispatcher.
It does not change package source, mathematical parameters or theorem flags.
"""
import argparse
from itertools import combinations,product
import json
from math import comb
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if '--installed' not in sys.argv:sys.path.insert(0,str(ROOT/'src'))
from veritas.research.manuscript import hashes
from veritas.research.manuscript.cnf import Formula,count
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.manuscript.resources import Budget,Limits,ResourceLimit
from veritas.research.manuscript.sparse import normalize_system


def distinct_rows(m,P,budget):
    if type(m) is not int or m<1 or type(P) is not int or P<0:raise ValueError('invalid list domain')
    budget.bits(m,'parity-row width');budget.items(min(m,P),'selected coordinates')
    total=0
    for k in range(min(m,P)+1):
        total+=comb(m,k);budget.bits(total.bit_length(),'distinct candidate count')
        if budget.limits.max_work is not None and total>budget.limits.max_work-budget.work:
            raise ResourceLimit('distinct parity-row enumeration exceeds allowance')
    for weight in range(min(m,P)+1):
        for selected in combinations(range(m),weight):
            budget.tick();yield sum(1<<e for e in selected)


def factor_query(original,n,equations,*,limits=Limits(),budget=None,event_sink=None):
    budget=Budget(limits) if budget is None else budget
    system=normalize_system(n,equations)
    budget.tick(sum(1+len(monomial) for eq in system for monomial in eq))
    active=sorted({v for eq in system for monomial in eq for v in monomial})
    budget.items(len(active),'active variable map');budget.bits(n+1,'factored exact count')
    if not active:
        value=0 if any(eq for eq in system) else 1<<n
        return dict(status='PASS_EXACT_COUNT',count=value,route='EXACT_UNUSED_VARIABLE_FACTOR',source_qualified=False,ledger=budget.report())
    if len(active)==n:return original(n,system,limits=limits,budget=budget,event_sink=event_sink)
    mapping={v:i for i,v in enumerate(active)}
    reduced=tuple(tuple(frozenset(mapping[v] for v in monomial) for monomial in eq) for eq in system)
    receipt=original(len(active),reduced,limits=limits,budget=budget,event_sink=event_sink)
    if receipt['status']!='PASS_EXACT_COUNT':return receipt
    return dict(status='PASS_EXACT_COUNT',count=receipt['count'] << (n-len(active)),
                route='EXACT_UNUSED_VARIABLE_FACTOR',inner_route=receipt['route'],
                active_variables=len(active),unused_variables=n-len(active),source_qualified=False,ledger=budget.report())


def produce(n=20,clauses=None,*,limits=Limits(max_work=10000000,max_seconds=120),integrated=False):
    clauses=[[1,2],[3,-4]] if clauses is None else clauses
    events=[];original_rows=hashes.greedy_rows;original_query=hashes.common_zeros
    if integrated:
        from veritas.research.manuscript.optimizations import count_optimized
        def trace(event):
            if event['kind']=='hash_start':
                events.append({key:value for key,value in event.items() if key!='kind'}|{'rounds':[]})
            elif event['kind']=='hash_round':
                if event['index']!=len(events[-1]['rounds']):raise ValueError('hash trace order')
                events[-1]['rounds'].append({key:value for key,value in event.items() if key not in ('kind','index')})
            else:raise ValueError('unexpected hash event')
        report=count_optimized(Formula(n,tuple(map(tuple,clauses))),limits=limits,hash_event_sink=trace)
        return dict(schema='VERITAS_DISTINCT_HASH_EXPERIMENT_V1',formula=dict(n=n,clauses=clauses),report=report,
                    greedy_events=events,optimization='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR',
                    source_qualified=False,executable_refinement_proven=False,complexity_proven=False)
    def query(n,equations,**kwargs):return factor_query(original_query,n,equations,**kwargs)
    def greedy(n,clauses,A0,P,*,limits=limits,budget=None):
        budget=Budget(limits) if budget is None else budget
        violation=[hashes.clause_violation_polynomial(c) for c in clauses];rows=list(A0)
        event=dict(n=n,clauses=[list(c) for c in clauses],P=P,initial_rows=list(A0),rounds=[])
        budget.items(len(events)+1,'greedy event transcript');events.append(event)
        for _ in range(3*n):
            best_count=None;best_row=None;scores=[]
            for word in distinct_rows(len(clauses),P,budget):
                receipt=query(n,hashes.system_equations(rows+[word],violation),limits=limits,budget=budget)
                if receipt['status']!='PASS_EXACT_COUNT':raise ResourceLimit('candidate count: '+receipt['status'])
                value=receipt['count'];budget.items(len(scores)+1,'candidate score transcript');scores.append([word,value])
                if best_count is None or value<best_count:best_row,best_count=word,value
            budget.items(len(event['rounds'])+1,'greedy rounds transcript')
            event['rounds'].append(dict(scores=scores,selected=best_row,count=best_count));rows.append(best_row)
        return tuple(rows)
    try:
        hashes.greedy_rows=greedy;hashes.common_zeros=query
        report=count(Formula(n,tuple(map(tuple,clauses))),limits=limits)
    finally:
        hashes.greedy_rows=original_rows;hashes.common_zeros=original_query
    return dict(schema='VERITAS_DISTINCT_HASH_EXPERIMENT_V1',formula=dict(n=n,clauses=clauses),report=report,
                greedy_events=events,optimization='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR',
                source_qualified=False,executable_refinement_proven=False,complexity_proven=False)


def need(ok,message):
    if not ok:raise ReplayError(message)


def replay(certificate):
    need(set(certificate)=={'schema','formula','report','greedy_events','optimization','source_qualified','executable_refinement_proven','complexity_proven'},'certificate fields')
    need(certificate['schema']=='VERITAS_DISTINCT_HASH_EXPERIMENT_V1','schema')
    need(certificate['optimization']=='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR','optimization')
    need(certificate['report']['status']=='PASS_EXACT_COUNT','incomplete producer')
    report_keys={'status','count','route','leaves','occurrence_bound','ledger','source_qualified','complexity_proven','arbitrary_density'}
    if 'optimization_policy' in certificate['report']:
        report_keys|={'optimization_policy','executable_refinement_proven'}
        need(certificate['report']['optimization_policy']=='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR' and
             certificate['report']['executable_refinement_proven'] is False,'integrated policy')
    need(set(certificate['report'])==report_keys,'report fields')
    need(certificate['report']['arbitrary_density'] is True,'branch claim')
    for key in ('calls','interpolation_points','exponent_tuples','maximum_depth'):
        need(type(certificate['report']['ledger'][key]) is int and certificate['report']['ledger'][key]==0,'bounded-support route counters')
    need(certificate['report'].get('source_qualified') is False and certificate['report'].get('complexity_proven') is False,'producer qualification')
    need(certificate['report'].get('route')=='SPARSIFY_SPARSE_QUERY' and
         type(certificate['report'].get('leaves')) is int and certificate['report']['leaves']==1,'producer route')
    for key in ('source_qualified','executable_refinement_proven','complexity_proven'):
        need(certificate[key] is False,'unsupported qualification')
    formula=certificate['formula'];need(set(formula)=={'n','clauses'},'formula fields');n=formula['n'];clauses=formula['clauses']
    need(type(n) is int and 20<=n<=1000 and isinstance(clauses,list) and clauses,'formula')
    need(all(isinstance(c,list) and c and all(type(lit) is int and 1<=abs(lit)<=n for lit in c) for c in clauses),'literals')
    need(len(clauses)<=8,'finite clause cap')
    active=sorted({abs(lit) for c in clauses for lit in c});need(len(active)<=16,'independent active-variable cap')
    need(3*n*2**(len(clauses)+len(active))<=10000000,'independent score-work cap')
    assignments=[];sat=0
    for values in product((False,True),repeat=len(active)):
        assignment=dict(zip(active,values));bad=[not any(assignment[abs(lit)] if lit>0 else not assignment[abs(lit)] for lit in c) for c in clauses]
        assignments.append((assignment,bad));sat+=not any(bad)
    expected=sat << (n-len(active));events=certificate['greedy_events']
    # This finite artifact deliberately checks one unsplit normalized sparse
    # leaf. Additional sparsification leaves require an independent tree replay.
    need(len(events)==1,'replay supports one unsplit sparse leaf')
    event=events[0];need(set(event)=={'n','clauses','P','initial_rows','rounds'},'greedy event fields')
    need(event['n']==n and {frozenset(c) for c in event['clauses']}=={frozenset(c) for c in clauses},
         'sparsification differs; independent tree replay required')
    leaf_clauses=event['clauses']
    assignments=[(assignment,[not any(assignment[abs(lit)] if lit>0 else not assignment[abs(lit)]
                  for lit in clause) for clause in leaf_clauses]) for assignment,_ in assignments]
    P=event['P'];m=len(leaf_clauses);need(type(P) is int and P>=0,'list length')
    need(1<=m<=8 and len({frozenset(c) for c in leaf_clauses})==m,'finite leaf clause cap')
    # Independently recover the unchanged quantitative parameters for this
    # unsplit leaf, including the original enormous ordered-list length.
    k=max(map(len,clauses));need(k>=2,'non-unit general branch required')
    lam=(n-1).bit_length();sigma=next(j for j in range(1,33) if j*j>=lam)
    gamma=2*(3**(k-1)-1);M=None
    for exponent in range(64):
        trial=2**exponent
        if trial<gamma:continue
        C=4*((3*trial)**(k-1)-1)//(3*trial-1)
        h=(4*C*trial-1).bit_length()
        if gamma*h*sigma<=trial:M=trial;break
    need(M is not None,'sparsification parameter cap')
    B=2*(M**k-1)//(M-1);mu=m.bit_length()
    need(type(certificate['report'].get('occurrence_bound')) is int and certificate['report']['occurrence_bound']==B,'occurrence bound mismatch')
    need(P==20000*B*B*mu*mu,'original hash-list length mismatch')
    need(m<=320000*B*B*mu**3 and m<100*B*mu,'checker requires q=1 zero-local-code regime')
    need(event['initial_rows']==[0]*(2*((m+8*B-1)//(8*B))),'initial Tanner rows mismatch')
    rows=event['initial_rows'];need(all(type(row) is int and 0<=row<2**m for row in rows),'initial parity rows')
    # Any initial parity equations implied by clause satisfaction are valid;
    # each recorded candidate score is recomputed from original literals below.
    need(len(event['rounds'])==3*n,'round count')
    candidates=sorted((word for word in range(2**m) if word.bit_count()<=P),
                      key=lambda word:(word.bit_count(),tuple(i for i in range(m) if word>>i&1)))
    need(3*n*len(candidates)*len(assignments)<=10000000,'independent score-work cap')
    checked=0
    for round in event['rounds']:
        need(set(round)=={'scores','selected','count'},'round fields')
        scores=[]
        for word in candidates:
            total=0
            for _,bad in assignments:
                bits=sum(int(value)<<i for i,value in enumerate(bad))
                total+=all((row&bits).bit_count()%2==0 for row in rows+[word])
            scores.append([word,total << (n-len(active))]);checked+=1
        need(round['scores']==scores,'independent candidate scores mismatch')
        best=min(range(len(scores)),key=lambda i:scores[i][1]);word,value=scores[best]
        need(type(round['selected']) is int and round['selected']==word and round['count']==value,'greedy minimum or tie mismatch')
        rows=rows+[word]
    need(type(certificate['report']['count']) is int and certificate['report']['count']==expected,'exact original-CNF count mismatch')
    final=sum(all((row&sum(int(v)<<i for i,v in enumerate(bad))).bit_count()%2==0 for row in rows) for _,bad in assignments) << (n-len(active))
    need(final==expected,'final parity system differs from CNF')
    return dict(status='PASS_INDEPENDENT_DISTINCT_HASH_REPLAY',n=n,exact_count=expected,
                active_variables=len(active),factored_unused_variables=n-len(active),
                independently_checked_candidate_scores=checked,greedy_rounds=3*n,
                original_ordered_list_length=P,distinct_candidates_per_round=len(candidates),
                source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
                scope='FINITE UNSPLIT LEAF; EXACT OPTIMIZATION; NOT SOURCE ACTIVE RECURSION')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--installed',action='store_true');parser.add_argument('--integrated',action='store_true')
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--replay',type=Path);args=parser.parse_args()
    if args.installed:
        if ROOT/'src' in Path(hashes.__file__).resolve().parents:parser.error('checkout source imported')
    if args.replay:
        if args.replay.stat().st_size>20_000_000:parser.error('certificate byte cap')
        print(json.dumps(replay(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay required')
    out=args.output_dir.resolve()
    if out==ROOT or ROOT in out.parents:parser.error('evidence must be external')
    out.mkdir(parents=True,exist_ok=True);certificate=produce(integrated=args.integrated)
    (out/'distinct_hash_certificate.json').write_text(json.dumps(certificate,indent=2)+'\n')
    if certificate['report']['status']!='PASS_EXACT_COUNT':print(json.dumps(certificate['report'],indent=2));raise SystemExit(2)
    result=replay(certificate);(out/'independent_hash_replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()

"""Verify explicit finite-degree fallback on original sparse equations.

This is direct-branch evidence, not recursive execution or a speed theorem.
The independent checker uses original Boolean assignments and composition
search rather than the producer's degree-admission dynamic program.
"""
import argparse
from dataclasses import asdict
from itertools import product
import json
from math import comb,isqrt
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
if '--installed' not in sys.argv:sys.path.insert(0,str(ROOT/'src'))
from veritas.research.manuscript.sparse_query import common_zeros
from veritas.research.manuscript.resources import Limits
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.tapered_v4.provenance import source_binding


def need(ok,message):
    if not ok:raise ReplayError(message)


def produce(*,limits=Limits(max_work=500000000,max_seconds=300)):
    wide=[[[v] for v in range(20)] for _ in range(9)]
    cases=[]
    for name,equations in (('wide_parity',wide),('heavy_parity',wide+[[[0]]]*100)):
        report=common_zeros(20,equations,limits=limits)
        cases.append(dict(name=name,n=20,equations=equations,report=report))
    return dict(schema='VERITAS_SPARSE_DEGREE_EXCEPTION_V2',producer_source_sha256=source_binding()['digest'],
                limits=asdict(limits),cases=cases)


class Meter:
    def __init__(self,max_work=100000000,max_seconds=120):
        need(type(max_work) is int and max_work>0,'positive checker work allowance')
        need(type(max_seconds) in (int,float) and 0<max_seconds<float('inf'),'positive checker time allowance')
        self.work=0;self.max_work=max_work;self.seconds=max_seconds;self.started=monotonic()
    def tick(self,n=1):
        self.work+=n
        need(self.work<=self.max_work and monotonic()-self.started<=self.seconds,'INCONCLUSIVE_RESOURCE_LIMIT: independent oracle allowance')


def normalized(n,equations,meter):
    need(type(n) is int and 1<=n<=20,'INCONCLUSIVE_RESOURCE_LIMIT: variable oracle cap')
    need(type(equations) is list and len(equations)<=128,'equation inventory')
    system=[]
    for equation in equations:
        need(type(equation) is list and len(equation)<=128,'monomial inventory');terms=set()
        for monomial in equation:
            need(type(monomial) is list and len(monomial)<=20 and all(type(v) is int and 0<=v<n for v in monomial),'monomial coordinates')
            meter.tick(len(monomial)+1);term=frozenset(monomial)
            if term in terms:terms.remove(term)
            else:terms.add(term)
        system.append(frozenset(terms))
    return tuple(system)


def boolean_count(n,system,meter):
    # Repeated equations impose the same constraint. This independent oracle
    # may deduplicate them; the producer admission analysis retains them.
    masks={tuple(sorted(sum(1<<v for v in term) for term in eq)) for eq in system}
    answer=0
    for assignment in range(1<<n):
        meter.tick();satisfied=True
        for equation in masks:
            meter.tick(len(equation)+1)
            if sum((assignment&mask)==mask for mask in equation)%2:
                satisfied=False;break
        answer+=satisfied
    return answer


def balanced(items,J):
    size,extra=divmod(len(items),J);offset=0;groups=[]
    for j in range(J):
        stop=offset+size+(j<extra);groups.append(items[offset:stop]);offset=stop
    return groups


def independent_degree(system,free,n,meter):
    lam=(n-1).bit_length();nu=(lam-1).bit_length();s=n*nu
    limit=next(d for d in range(1,s+1) if d**10>=s**9)
    J=next(j for j in range(1,n+1) if j**4>=n)
    k=max((len(m) for eq in system for m in eq),default=0);K=k*(len(system)+2*n)
    tests=balanced(list(range(len(system))),J);variables=balanced(list(free),J)
    scopes=[set().union(*eq) if eq else set() for eq in system]
    sizes=[[sum(len(scopes[i].intersection(group)) for i in test) for group in variables] for test in tests]
    largest=0;witness=None
    for side,groups in (('row',sizes),('column',list(zip(*sizes)))):
        for index,Ns in enumerate(groups):
            meter.tick()
            # Independent finite composition search; no producer knapsack.
            widths=[[(comb(N,d)-1).bit_length() for d in range(min(N,K)+1)] for N in Ns]
            maximum=0
            for ds in product(*(range(len(row)) for row in widths)):
                meter.tick()
                if sum(ds)<=K:maximum=max(maximum,sum(row[d] for row,d in zip(widths,ds)))
            if maximum>largest:
                largest=maximum;witness=(side,index)
    return dict(degree=largest,limit=limit,side=witness[0],group=witness[1]) if largest>limit else None


def replay(certificate,*,max_work=100000000,max_seconds=120):
    meter=Meter(max_work,max_seconds)
    need(type(certificate) is dict and set(certificate)=={'schema','producer_source_sha256','limits','cases'},'certificate fields')
    need(certificate['schema'] in ('VERITAS_SPARSE_DEGREE_EXCEPTION_V1',
                                  'VERITAS_SPARSE_DEGREE_EXCEPTION_V2'),'schema')
    # V1 receipts retain their historical grouping, including zero equations.
    # V2 follows the paper's discard rule; both are independently recomputed.
    discard_zero = certificate['schema']=='VERITAS_SPARSE_DEGREE_EXCEPTION_V2'
    pin=certificate['producer_source_sha256']
    # Numerical replay does not authenticate producer code. None explicitly
    # marks an unpinned development receipt instead of inventing provenance.
    need(pin is None or type(pin) is str and len(pin)==64 and all(c in '0123456789abcdef' for c in pin),'producer digest format')
    limits=certificate['limits'];need(type(limits) is dict and set(limits)=={'max_work','max_seconds','max_items','max_integer_bits'},'producer limits')
    for key in ('max_work','max_items','max_integer_bits'):need(type(limits[key]) is int and limits[key]>0,'producer allocation allowance')
    need(type(limits['max_seconds']) in (int,float) and 0<limits['max_seconds']<float('inf'),'producer time allowance')
    cases=certificate['cases'];need(type(cases) is list and 1<=len(cases)<=2,'case inventory');results=[]
    for case in cases:
        need(type(case) is dict and set(case)=={'name','n','equations','report'} and type(case['name']) is str,'case fields')
        n=case['n'];system=normalized(n,case['equations'],meter)
        need(n>=20,'this oracle requires nontrivial source admission')
        report=case['report']
        need(type(report) is dict,'report fields')
        if report.get('status')=='INCONCLUSIVE_RESOURCE_LIMIT':raise ReplayError('INCONCLUSIVE_RESOURCE_LIMIT: producer did not complete')
        need(set(report)=={'status','count','route','ledger','source_qualified','complexity_proven',
            'degree_admission_fallback_branches','largest_fallback_degree','source_degree_limit','fallback_policy'},'report fields')
        need(report.get('status')=='PASS_EXACT_COUNT','producer status')
        need(report.get('source_qualified') is False and report.get('complexity_proven') is False,'unsupported qualification')
        need(report.get('route')=='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT' and report.get('fallback_policy')=='EXACT_DEGREE_PREFLIGHT_AND_ORIGINAL_FREE_VARIABLE_COUNT','fallback route or policy')
        original=boolean_count(n,system,meter)
        need(type(report.get('count')) is int and report['count']==original,'original equation count mismatch')
        lam=(n-1).bit_length();sqrt=isqrt(lam)+(isqrt(lam)**2<lam)
        scopes=[set().union(*eq) if eq else set() for eq in system];N0=sum(map(len,scopes))
        threshold=max(1,(N0+n-1)//n)*sqrt
        heavy=[v for v in range(n) if sum(v in scope for scope in scopes)>threshold]
        fallback=largest=0;limit=None
        for assignment in range(1<<len(heavy)):
            fixed={v:(assignment>>j)&1 for j,v in enumerate(heavy)};branch=[];died=False
            for equation in system:
                terms=set()
                for monomial in equation:
                    meter.tick()
                    if any(v in fixed and fixed[v]==0 for v in monomial):continue
                    reduced=frozenset(v for v in monomial if v not in fixed)
                    if reduced in terms:terms.remove(reduced)
                    else:terms.add(reduced)
                if terms=={frozenset()}:died=True;break
                if terms or not discard_zero:
                    branch.append(frozenset(terms))
            if died or not branch:continue
            free=[v for v in range(n) if v not in fixed]
            witness=independent_degree(branch,free,n,meter)
            need(witness is not None,'oracle fixture includes a tensor branch, outside direct-only evidence scope')
            fallback+=1;largest=max(largest,witness['degree']);limit=witness['limit']
        for key,value in dict(degree_admission_fallback_branches=fallback,largest_fallback_degree=largest,source_degree_limit=limit).items():
            need(type(report.get(key)) is int and report[key]==value,'degree diagnosis mismatch: '+key)
        ledger=report.get('ledger');need(type(ledger) is dict and set(ledger)=={'work_units','elapsed_seconds','calls','interpolation_points','exponent_tuples','maximum_depth','bit_operations','hard_memory_limit_enforced'},'ledger')
        for key in ('calls','interpolation_points','exponent_tuples','maximum_depth'):need(type(ledger.get(key)) is int and ledger[key]==0,'unexpected tensor execution')
        need(type(ledger.get('work_units')) is int and 0<ledger['work_units']<=limits['max_work'],'producer work allowance')
        need(type(ledger.get('elapsed_seconds')) in (int,float) and 0<=ledger['elapsed_seconds']<=limits['max_seconds'],'producer time allowance')
        need(ledger.get('bit_operations') is None and ledger.get('hard_memory_limit_enforced') is False,'unsupported resource claim')
        results.append(dict(name=case['name'],count=original,heavy_variables=heavy,fallback_branches=fallback,checked_degree=largest,degree_limit=limit))
    return dict(status='PASS_INDEPENDENT_SPARSE_DEGREE_EXCEPTION_REPLAY',cases=results,
                producer_source_sha256=pin,checker_source_sha256=source_binding()['digest'],
                producer_source_identity='UNRECORDED_DEVELOPMENT' if pin is None else 'UNSIGNED_SHA256_RECORDED',
                oracle_work_units=meter.work,oracle_elapsed_seconds=monotonic()-meter.started,
                oracle_limits=dict(max_work=max_work,max_seconds=max_seconds,variables=20,equations=128),
                source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
                evidence_scope='EXACT_DIRECT_BRANCH_COUNTS_NOT_RECURSIVE_EXECUTION')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed',action='store_true')
    p.add_argument('--output-dir',type=Path);p.add_argument('--replay',type=Path);args=p.parse_args()
    if args.installed:
        import veritas
        need(not Path(veritas.__file__).resolve().is_relative_to(ROOT/'src'),'installed check imported checkout')
    try:
        if args.replay:
            need(args.replay.stat().st_size<=1000000,'INCONCLUSIVE_RESOURCE_LIMIT: certificate byte cap')
            certificate=json.loads(args.replay.read_text())
        else:
            if args.output_dir is None:p.error('--output-dir required')
            need(not args.output_dir.resolve().is_relative_to(ROOT),'evidence must be external')
            args.output_dir.mkdir(parents=True,exist_ok=True);certificate=produce()
            (args.output_dir/'certificate.json').write_text(json.dumps(certificate,separators=(',',':')))
        result=replay(certificate)
    except (ReplayError,ValueError,TypeError,KeyError,OverflowError) as exc:
        result=dict(status='INCONCLUSIVE_RESOURCE_LIMIT' if 'INCONCLUSIVE_RESOURCE_LIMIT' in str(exc) else 'FAIL_REPLAY',reason=str(exc))
    if args.output_dir:
        need(not args.output_dir.resolve().is_relative_to(ROOT),'evidence must be external');args.output_dir.mkdir(parents=True,exist_ok=True)
        (args.output_dir/'independent_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['status']=='PASS_INDEPENDENT_SPARSE_DEGREE_EXCEPTION_REPLAY' else 1


if __name__=='__main__':raise SystemExit(main())

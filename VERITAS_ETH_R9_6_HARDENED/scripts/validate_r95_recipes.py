#!/usr/bin/env python3
"""Regenerate bounded entry/leaf and source-precision evidence; never theorem evidence."""
from dataclasses import asdict
from itertools import product
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import platform
import random
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from veritas.core.cnf import CNF
from veritas.research.math_exact.oracle import exhaustive_count
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.source_cnf import source_cnf_network
from veritas.research.source_cnf_check import check_source_cnf_network
from veritas.research.tapered_v4.source_recipes import make_reference,evaluate_source_entry,EntryLimits
from veritas.research.tapered_v4.source_leaf import contract_source_leaf,SourceLeafPolicy
from veritas.research.tapered_v4.source_state import SourceContext
from veritas.research.tapered_v4.source_recipe_bridge import source_node_from_described
from veritas.research.independent_r95.recipe_oracle import evaluate_reference
from veritas.research.independent_r95.hermite_grid import check_grid


def manifest():
    files=[]
    for directory in ('src','proofs','tests','paper','scripts'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in ('.py','.lean','.tex'))
    files.extend(ROOT/p for p in ('lean-toolchain','pyproject.toml'))
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def validate():
    report={'schema':'VERITAS_R95_RECIPE_VALIDATION_V1','status':'NOT_RUN',
        'python':platform.python_version(),'platform':platform.platform(),
        'policy':{'seed':9505,'packet_fixtures':32,'entry_limits':asdict(EntryLimits()),
                  'leaf_policy':asdict(SourceLeafPolicy(verify_independent=True))},
        'checks_executed':{'entry_equalities':0,'leaf_equalities':0,'hermite_points':0},
        'source_manifest':manifest(),'theorem_mode_enabled':False,
        'executable_refinement_proven':False,'complete_recursive_identity_proven':False,
        'complete_bit_complexity_proven':False,'hard_memory_limit_enforced':False,
        'limitations':['Packet oracle uses separate integer polynomial arithmetic and full coefficient convolution.',
          'Leaf oracle uses variable elimination; both paths share the wire schema and SourceNode data.',
          'CNF structure and exhaustive counting checks share the CNF model, not the tensor evaluator.',
          'These are finite cases. Actual source-active recursion and uniform entry-cost bounds remain unimplemented.']}
    start=time.perf_counter();cpu=time.process_time();rng=random.Random(9505)
    try:
        for seed in range(32):
            nr=seed%3;nc=seed//3%3;arity=nr+nc;p=1+seed%5;ell=1+seed%2;f=(7,11,13)[seed%3];e=f.bit_length()-1
            jet=lambda:tuple(tuple(rng.randrange(2**p) for _ in range(e)) for _ in range(ell))
            data=[list(range(nr)),list(range(nr,arity)),[[jet() for _ in range(nc)] for _ in range(nr)],
                  [[rng.randrange(3),[jet() for _ in range(nr)]] for _ in range(seed%3)],
                  [[rng.randrange(3),[rng.randrange(2**p) for _ in range(nc)]] for _ in range(seed%2)]]
            ref=make_reference(kind='packet',arity=arity,creation_precision=p,defining_polynomial=f,jet_length=ell,data=data)
            for bits in product((0,1),repeat=arity):
                if evaluate_source_entry(ref,bits,precision=p+3)['result']!=evaluate_reference(ref,bits,precision=p+3):
                    raise ValueError('packet entry mismatch')
                report['checks_executed']['entry_equalities']+=1
        leaves=[]
        for clauses in ((),((),),((1,),),((1,1),),((1,-1),),((1,2),),((1,),(-1,)),((1,),(-2,)),((1,2),(-1,2))):
            cnf=CNF(3,clauses);ctx=SourceContext(8,2,1,2,4,1,first_irreducible(12))
            encoded=source_cnf_network(cnf)
            if not check_source_cnf_network(cnf,encoded)['valid']:raise ValueError('CNF incidence mismatch')
            graph=describe_integer_network(encoded.network,creation_precision=4,defining_polynomial=ctx.defining_polynomial)
            node=source_node_from_described(graph,ctx,depth=0,precision=4)
            result=contract_source_leaf(node,SourceLeafPolicy(verify_independent=True))
            if result['status']!='EXACT_SOURCE_LEAF_MODULAR_CONTRACTION':raise ValueError(str(result))
            count=result['result'][0][0]*2**len(encoded.unused_variables)
            if count!=exhaustive_count(cnf):raise ValueError('CNF count mismatch')
            leaves.append({'clauses':clauses,'edges':graph.edges,'count':count,'result':result})
            report['checks_executed']['leaf_equalities']+=1
        report['leaf_cases']=leaves
        report['hermite_cases']=[check_grid(a=a,u=u,M=M,p=5) for a,u,M in
            ((1,1,1),(1,1,3),(2,1,2),(2,2,2),(3,1,1),(3,2,2),(3,3,3),(4,3,5),(5,5,7),(6,4,10))]
        report['checks_executed']['hermite_points']=sum(r['points_checked'] for r in report['hermite_cases'])
        if manifest()!=report['source_manifest']:raise ValueError('source changed during validation')
        report['status']='PASS_FINITE_RECIPE_LEAF_AND_GRID'
    except (ValueError,TypeError,ArithmeticError,MemoryError,RecursionError) as exc:
        report.update(status='FAIL_OR_INCOMPLETE',error=str(exc).replace(str(ROOT),'<repository>'))
    report['elapsed_seconds']=time.perf_counter()-start;report['cpu_seconds']=time.process_time()-cpu
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['process_peak_rss_bytes']=rss if sys.platform=='darwin' else rss*1024
    report['source_manifest_sha256']=sha256(json.dumps(report['source_manifest'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=(str(Path(os.environ['VERITAS_EVIDENCE_DIR'])/'r9_5_recipes.json') if os.environ.get('VERITAS_EVIDENCE_DIR') else 'validation/r9_5_recipes.json'));args=parser.parse_args()
    report=validate();path=ROOT/args.output;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('status','checks_executed','elapsed_seconds')}))
    return 0 if report['status']=='PASS_FINITE_RECIPE_LEAF_AND_GRID' else 1

if __name__=='__main__':raise SystemExit(main())

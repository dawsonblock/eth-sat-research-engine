"""Bounded CNF input to two finite active levels to independently checked count.

This demonstration accepts n=2 and 2..3 literal occurrences with connected
incidence. It is not a general #SAT solver or the source-active manuscript
schedule. Modulo-four ambiguity is refused, never guessed or hidden by fallback.
"""
import argparse
from itertools import product
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_manuscript_connected_two_level as connected


def build_fixture(n,clauses):
    if type(n) is not int or n!=2:raise ValueError('finite CNF demonstration requires n=2')
    if not isinstance(clauses,list) or not clauses or any(not isinstance(c,list) or not c for c in clauses):
        raise ValueError('nonempty clauses required')
    if any(type(lit) is not int or not 1<=abs(lit)<=n for c in clauses for lit in c):
        raise ValueError('invalid literal')
    M=sum(map(len,clauses))
    if not 2<=M<=3:raise ValueError('finite CNF demonstration requires 2..3 occurrences')
    occurrences=[];edge=0;column_vertices=[]
    for index,clause in enumerate(clauses):
        ports=[]
        for lit in clause:occurrences.append((abs(lit),edge));ports.append(edge);edge+=1
        table=[]
        for assignment in range(2**len(ports)):
            satisfied=any(bool((assignment>>j)&1)==(lit>0) for j,lit in enumerate(clause))
            table.append([int(satisfied),0])
        column_vertices.append(dict(side='column',identity=index,ports=ports,values=table))
    vertices=[]
    for variable in range(1,n+1):
        ports=[e for v,e in occurrences if v==variable]
        table=[]
        for assignment in range(2**len(ports)):
            bits=[(assignment>>j)&1 for j in range(len(ports))]
            table.append([2 if not bits else int(all(b==bits[0] for b in bits)),0])
        vertices.append(dict(side='row',identity=variable-1,ports=ports,values=table))
    return dict(wires=M,precision=2,ell=2,vertices=vertices+column_vertices)


def produce(n=2,clauses=None):
    clauses=[[1,2]] if clauses is None else clauses
    fixture=build_fixture(n,clauses)
    return dict(schema='VERITAS_TINY_CNF_TWO_LEVEL_V1',formula=dict(n=n,clauses=clauses),
                tensor_certificate=connected.produce(fixture))


def replay(certificate):
    check=connected.need
    check(set(certificate)=={'schema','formula','tensor_certificate'},'CNF certificate fields')
    check(certificate['schema']=='VERITAS_TINY_CNF_TWO_LEVEL_V1','CNF schema')
    formula=certificate['formula'];check(set(formula)=={'n','clauses'},'formula fields')
    n=formula['n'];clauses=formula['clauses']
    check(type(n) is int and n==2 and isinstance(clauses,list) and bool(clauses),'formula dimensions')
    check(all(isinstance(c,list) and c and all(type(lit) is int and 1<=abs(lit)<=2 for lit in c) for c in clauses),'literal syntax')
    flat=[(clause_index,position,lit) for clause_index,c in enumerate(clauses) for position,lit in enumerate(c)]
    check(2<=len(flat)<=3,'occurrence cap')
    fixture=certificate['tensor_certificate']['fixture'];graph=connected.decode_fixture(fixture)
    check(fixture['wires']==len(flat) and len(graph['vertices'])==2+len(clauses),'incidence dimensions')
    # Independently verify every port and every truth-table entry against the
    # original formula; do not invoke the producer's build_fixture conversion.
    for index,vertex in enumerate(fixture['vertices']):
        is_row=index<2
        expected_ports=[edge for edge,(_,_,lit) in enumerate(flat) if abs(lit)==index+1] if is_row else [
            edge for edge,(ci,_,_) in enumerate(flat) if ci==index-2]
        check(connected.same([vertex['side'],vertex['identity'],vertex['ports']],
                             ['row' if is_row else 'column',index if is_row else index-2,expected_ports]),'CNF incidence mismatch')
        for assignment,values in enumerate(vertex['values']):
            bits=tuple((assignment>>j)&1 for j in range(len(expected_ports)))
            if is_row:
                expected=2 if not bits else int(len(set(bits))==1)
            else:
                clause=clauses[index-2]
                # Integer signed-literal evaluation, independent of builder.
                expected=int(sum((bit if lit>0 else 1-bit) for bit,lit in zip(bits,clause))>0)
            check(connected.same(values,[expected,0]),'CNF truth table mismatch')
    recursive=connected.replay(certificate['tensor_certificate'])
    # Trusted separate exact oracle enumerates original variable assignments,
    # not tensor half-edges, packet slots or descendants.
    solutions=[]
    for bits in product((False,True),repeat=n):
        if all(any(bits[abs(lit)-1] if lit>0 else not bits[abs(lit)-1] for lit in clause) for clause in clauses):
            solutions.append(list(map(int,bits)))
    count=len(solutions)
    check(count<4,'AMBIGUOUS_MODULUS: exact count does not fit root precision')
    check(recursive['root_modular_jet']==[count,0],'CNF exact oracle disagrees with recursive value')
    return dict(status='PASS_TINY_CNF_TWO_LEVEL_END_TO_END',n=n,clauses=clauses,exact_count=count,
                independent_satisfying_assignments=solutions,recursive_replay=recursive,
                source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
                scope='N=2; CONNECTED 2..3 OCCURRENCES; TWO SCALED LEVELS; INDEPENDENT EXACT ORACLE')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--installed',action='store_true')
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--replay',type=Path);args=parser.parse_args()
    if args.installed:
        from veritas.research.manuscript import executor
        if ROOT/'src' in Path(executor.__file__).resolve().parents:parser.error('checkout source imported')
    if args.replay:
        if args.replay.stat().st_size>20_000_000:parser.error('certificate byte cap')
        print(json.dumps(replay(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay required')
    out=args.output_dir.resolve()
    if out==ROOT or ROOT in out.parents:parser.error('evidence must be external')
    out.mkdir(parents=True,exist_ok=True);certificate=produce()
    path=out/'tiny_cnf_two_level.json';path.write_text(json.dumps(certificate,indent=2)+'\n')
    result=replay(json.loads(path.read_text()));(out/'independent_tiny_cnf_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

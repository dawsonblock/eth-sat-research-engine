from dataclasses import replace
from itertools import product
import pytest
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.tapered_v4.source_recipes import make_reference
from veritas.research.tapered_v4.source_state import SourceVertex
from veritas.research.parent_child_r98.model import ParentCall,PacketLayout,Budget,canonical,decode
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r910.engine import contract
from veritas.research.parent_child_r910.checker import verify


def jet_matching(length=3, edges=22, precision=32):
    f=first_irreducible(4);vertices=[];tables=[]
    # Higher V coefficients interact; 0*V and modular cancellation are included.
    for side in ('row','column'):
        for e in range(edges):
            polys=([ [1,2,3],[3,-1,2] ] if side=='row' else [[2,1,-2],[5,3,1]]) if e==0 else [[1,0,0],[1,0,0]]
            data=[[[p[j] % (1<<precision),0,0,0] for j in range(length)] for p in polys]
            ref=make_reference(kind='dense',arity=1,creation_precision=precision,defining_polynomial=f,
                jet_length=length,data=data)
            vertices.append(SourceVertex(side,e,(e,),ref));tables.append(polys)
    return ParentCall(max(32,2*edges),0,precision,f,edges,tuple(vertices),jet_length=length)


def multilevel_layout(call,a,u,budget):
    base=construct_vertex_shrinking_layout(call,budget=budget).source
    base.update(a=a,L=1<<a,D=64**(2*a),H_pad=1<<a)
    # Cross in every coordinate. Each packet has a single real slot, and each
    # group inherits one row and one column port: actual children have 2 wires.
    rows={str(i):[i]*a for i in range(call.edge_count)}
    cols={str(i):[(i+1)%call.edge_count]*a for i in range(call.edge_count)}
    base['row_labels']=rows;base['column_labels']=cols
    base['packets']=sorted([{'symbol_pairs':[[min(i,(i+1)%call.edge_count),max(i,(i+1)%call.edge_count)]]*a,
        'index':0,'occupied_slots':[[((1<<a)-1)*int(i>(i+1)%call.edge_count),i]]}
        for i in range(call.edge_count)],key=lambda p:(p['symbol_pairs'],p['index']))
    result=PacketLayout(call.content_digest,a,u,canonical(base),'balanced_vertices')
    assert audit_layout(call,result)['group_load_bound_met']
    return result


def independent_matching_polynomial(parent):
    # Integer convolution, no production ring, evaluator, interpolation or child code.
    ell=parent.jet_length;answer=[1]+[0]*(ell-1)
    for edge in range(parent.edge_count):
        pair=[]
        for side in ('row','column'):
            ref=next(v.tensor for v in parent.vertices if v.side==side and v.ports==(edge,))
            pair.append([[c[0] for c in jet] for jet in decode(ref.description)['data']])
        local=[sum(pair[0][bit][i]*pair[1][bit][k-i] for bit in (0,1) for i in range(k+1)) for k in range(ell)]
        answer=[sum(answer[i]*local[k-i] for i in range(k+1)) % (1<<parent.precision) for k in range(ell)]
    return tuple((n,0,0,0) for n in answer)


@pytest.mark.parametrize('schedule',[((1,1),),((2,2),)])
def test_full_jet_recursion_and_independent_replay(schedule):
    parent=jet_matching();events=[]
    policy=replace(DEFAULT_SHRINKING_POLICY,max_work=100_000_000,max_seconds=600)
    report=contract(parent,schedule=schedule,policy=policy,layout_factory=multilevel_layout,
        evidence_sink=events.append,coefficient_encoding=True)
    assert report['status']=='PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION',report
    assert report['result']==independent_matching_polynomial(parent)
    assert any(c[0] for c in report["result"][1:])
    assert any(any(c[0] for c in decode(r).get('result',())[1:]) for r in events if decode(r)['kind']=='leaf')
    checked=verify(parent,events,report,policy=policy)
    assert checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY',checked
    assert checked['result']==report['result']


def test_ring_metadata_mismatch_and_cache_identity():
    parent=jet_matching()
    with pytest.raises(ValueError,match='ring mismatch'):replace(parent,jet_length=1)
    with pytest.raises(ValueError):replace(parent,jet_length=True)


def test_canonical_jet_cli_input_and_leaf_replay(tmp_path,capsys):
    from veritas.research.parent_child_r912.cli import load_parent,main
    parent=jet_matching(edges=1)
    source=tmp_path/'parent.json';source.write_bytes(canonical(parent.record()))
    assert load_parent(source)==parent
    output=tmp_path/'out'
    assert main([str(source),'--output-dir',str(output)])==0
    from veritas.research.parent_child_r99.cli import load_execution_report
    report=load_execution_report(output/'report.json',max_bytes=1_000_000)
    assert report['result']==list(map(list,independent_matching_polynomial(parent)))
    assert main([str(source),'--replay-dir',str(output),'--output-dir',str(tmp_path/'replay')])==0


def test_general_default_layout_has_checked_coordinate_loads():
    from veritas.research.parent_child_r912.layout import finite_layout
    parent=jet_matching()
    layout=finite_layout(parent,2,2,Budget(DEFAULT_SHRINKING_POLICY))
    assert layout.a==layout.u==2
    assert audit_layout(parent,layout)['group_load_bound_met']


def test_nested_full_jet_dependency_replay():
    parent=jet_matching(edges=235,precision=256);events=[]
    policy=replace(DEFAULT_SHRINKING_POLICY,max_work=300_000_000,max_seconds=600,
                   max_certificate_bytes=100_000_000)
    from pathlib import Path
    source=decode((Path(__file__).resolve().parents[1]/'examples/r910_matching235_layout.json').read_bytes())
    layout=PacketLayout(parent.content_digest,1,1,canonical(source['source']),source['strategy'])
    assert audit_layout(parent,layout)['group_load_bound_met']
    def factory(call,a,u,budget):
        return layout if call.depth==parent.depth else construct_vertex_shrinking_layout(call,budget=budget)
    report=contract(parent,schedule=((1,1),(1,1)),policy=policy,layout_factory=factory,
        evidence_sink=events.append,coefficient_encoding=True,compressed_records=True)
    assert report['status']=='PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION',report
    assert report['active_calls_by_depth']['1']>0
    assert report['largest_deformation_degree_by_depth']['1']>0
    assert report['result']==independent_matching_polynomial(parent)
    assert all(c[0] for c in report['result'])
    checked=verify(parent,events,report,policy=policy)
    assert checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY',checked
    assert checked['result']==report['result']

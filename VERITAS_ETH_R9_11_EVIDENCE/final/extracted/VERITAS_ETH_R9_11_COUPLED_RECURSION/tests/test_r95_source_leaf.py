from dataclasses import replace
from itertools import product
import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.math_exact.oracle import exhaustive_count
from veritas.research.source_cnf import source_cnf_network
from veritas.research.source_cnf_check import check_source_cnf_network
from veritas.research.tapered_v4.source_state import SourceContext,SourceNode,SourceVertex
from veritas.research.tapered_v4.source_recipes import make_reference,EntryLimits
from veritas.research.tapered_v4.source_leaf import SourceLeafPolicy,contract_source_leaf
from veritas.research.tapered_v4.source_recipe_bridge import source_node_from_described


def context(s=4,p=3):
    return SourceContext(s,2,1,2,p,1,first_irreducible(4*(s-1).bit_length()))


def reference(ctx,kind,arity,data,p=None):
    return make_reference(kind=kind,arity=arity,creation_precision=p or ctx.initial_precision,
                          defining_polynomial=ctx.defining_polynomial,jet_length=ctx.jet_length,data=data)


def parallel(ctx,m=1):
    r=reference(ctx,'equality',m,[])
    return SourceNode(ctx,m,tuple(SourceVertex(side,0,tuple(range(m)),r) for side in ('row','column')),0,ctx.initial_precision)


def test_empty_network_and_scalar():
    ctx=context();node=SourceNode(ctx,0,(),0,3)
    report=contract_source_leaf(node,SourceLeafPolicy(verify_independent=True))
    assert report['result']==((1,)+(0,)*(ctx.extension_degree-1),)
    assert report['independent_variable_elimination_checked']
    zero=reference(ctx,'clause',0,[])
    node=replace(node,vertices=(SourceVertex('row',0,(),zero),))
    assert contract_source_leaf(node)['result']==((0,)*ctx.extension_degree,)


@pytest.mark.parametrize('m',range(1,5))
def test_parallel_edge_occurrences(m):
    node=parallel(context(),m)
    report=contract_source_leaf(node,SourceLeafPolicy(verify_independent=True))
    assert report['status']=='EXACT_SOURCE_LEAF_MODULAR_CONTRACTION'
    assert report['result'][0][0]==2
    assert not report['theorem_mode_enabled'] and not report['executable_refinement_proven']


@pytest.mark.parametrize('clauses',[(),((),),((1,),),((1,1),),((1,-1),),((1,2),),((1,),(-1,)),((1,),(-2,))])
def test_cnf_to_source_leaf_with_independent_count(clauses):
    cnf=CNF(3,clauses);ctx=context(s=8,p=4)
    encoded=source_cnf_network(cnf)
    assert check_source_cnf_network(cnf,encoded)['valid']
    described=describe_integer_network(encoded.network,creation_precision=4,defining_polynomial=ctx.defining_polynomial)
    node=source_node_from_described(described,ctx,depth=0,precision=4)
    report=contract_source_leaf(node,SourceLeafPolicy(verify_independent=True))
    assert report['status']=='EXACT_SOURCE_LEAF_MODULAR_CONTRACTION',report
    assert report['result'][0][0]*2**len(encoded.unused_variables)==exhaustive_count(cnf)


def test_child_entry_canonical_lift_and_oracle():
    ctx=context(s=16);e=ctx.extension_degree
    scalar=lambda c:[[c]+[0]*(e-1)]
    packet=reference(ctx,'packet',3,[[0],[1,2],[[scalar(6),scalar(6)]],[],[]])
    one=reference(ctx,'clause',1,[1])
    vs=(SourceVertex('row',0,(0,1,2),packet),)+tuple(SourceVertex('column',i,(i,),one) for i in range(3))
    node=SourceNode(ctx,3,vs,1,7)
    result=contract_source_leaf(node,SourceLeafPolicy(verify_independent=True,oracle_max_work=5_000_000))
    assert result['status']=='EXACT_SOURCE_LEAF_MODULAR_CONTRACTION',result
    assert result['result'][0][0]==4  # Re-evaluating at p=7 would incorrectly produce 12.


def test_root_must_have_base_ring_entries():
    ctx=context();e=ctx.extension_degree
    dense=reference(ctx,'dense',0,[[[0,1]+[0]*(e-2)]])
    node=SourceNode(ctx,0,(SourceVertex('row',0,(),dense),),0,3)
    r=contract_source_leaf(node)
    assert r['status']=='INCONCLUSIVE_ROOT_COEFFICIENT_DOMAIN' and 'result' not in r


@pytest.mark.parametrize('failure',['unknown','changed_metadata','malformed'])
def test_zero_factor_cannot_hide_invalid_recipe(failure):
    ctx=context();zero=reference(ctx,'clause',0,[])
    bad=replace(zero,recipe_kind='unknown') if failure=='unknown' else replace(zero,description=zero.description.replace(b'"arity":0',b'"arity":1') if failure=='changed_metadata' else b'{')
    node=SourceNode(ctx,0,(SourceVertex('row',0,(),zero),SourceVertex('column',0,(),bad)),0,3)
    r=contract_source_leaf(node)
    assert r['status'].startswith('INCONCLUSIVE') and 'result' not in r


def test_nonleaf_never_uses_direct_answer():
    ctx=context(s=16);node=parallel(ctx,9)
    report=contract_source_leaf(node)
    assert report['status']=='INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED' and 'result' not in report
    report=contract_source_leaf(node,mode='theorem')
    assert report['status']=='INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED' and 'result' not in report


@pytest.mark.parametrize('policy,status',[
    (SourceLeafPolicy(max_edges=0),'INCONCLUSIVE_RESOURCE_LIMIT'),
    (SourceLeafPolicy(entry_limits=EntryLimits(max_work=1)),'INCONCLUSIVE_RESOURCE_LIMIT'),
    (SourceLeafPolicy(verify_independent=True,oracle_max_edges=0),'INCONCLUSIVE_ORACLE_COVERAGE'),
    (SourceLeafPolicy(verify_independent=True,oracle_max_work=1),'INCONCLUSIVE_ORACLE_RESOURCE_LIMIT'),
])
def test_failed_budgets_have_no_answer(policy,status):
    report=contract_source_leaf(parallel(context()),policy)
    assert report['status']==status and 'result' not in report


def test_corrupted_evaluation_detected_independently(monkeypatch):
    import veritas.research.tapered_v4.source_leaf as module
    ctx=context();node=parallel(ctx)
    monkeypatch.setattr(module,'evaluate_compiled',lambda *args: ((0,)*ctx.extension_degree,))
    report=contract_source_leaf(node,SourceLeafPolicy(verify_independent=True))
    assert report['status']=='INCONCLUSIVE_INVARIANT_FAILURE' and 'result' not in report


def test_cooperative_deadline(monkeypatch):
    import veritas.research.tapered_v4.source_recipes as module
    node=parallel(context());ticks=iter((0,100,200))
    monkeypatch.setattr(module,'monotonic',lambda:next(ticks,300))
    report=contract_source_leaf(node)
    assert report['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'result' not in report

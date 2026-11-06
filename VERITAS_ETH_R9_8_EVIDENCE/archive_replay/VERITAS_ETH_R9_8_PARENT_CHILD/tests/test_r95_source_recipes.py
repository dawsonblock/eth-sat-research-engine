"""Independent arithmetic/coefficients, creation precision and bridge tests."""
from dataclasses import replace
from itertools import product
import json
import random
import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
from veritas.research.eth_recursive_contraction_v39.described_network import CreatedDenseTensor,CreatedPacketTensor
from veritas.research.eth_recursive_contraction_v39.lazy_children import PacketTensorEntry,_Budget
from veritas.research.tapered_v4.source_recipes import EntryLimits,make_reference,evaluate_source_entry,compile_entry,EntryBudget
from veritas.research.tapered_v4.source_recipe_bridge import source_reference_from_created
from veritas.research.tapered_v4.source_state import SourceAdmissionError
from veritas.research.independent_r95.recipe_oracle import evaluate_reference,ReferenceArithmetic


def ref(kind,arity,data,p=3,f=7,ell=1):
    return make_reference(kind=kind,arity=arity,creation_precision=p,defining_polynomial=f,jet_length=ell,data=data)


def value(r,bits,p=7):return evaluate_source_entry(r,bits,precision=p)['result']


@pytest.mark.parametrize('f',[7,11,13])
@pytest.mark.parametrize('p',[1,3,7])
def test_independent_ring_random_and_every_dense_index(f,p):
    rng=random.Random(9500+f+p);ring=JetRing(ExtensionRing(p,f),2)
    ar=ReferenceArithmetic(p,f,2,1_000_000)
    entries=[tuple(tuple(rng.randrange(2**p) for _ in range(ring.base.e)) for _ in range(2)) for _ in range(8)]
    r=ref('dense',3,entries,p,f,2)
    for bits,want in zip(product((0,1),repeat=3),entries):
        assert value(r,bits,max(p,7))==evaluate_reference(r,bits,precision=max(p,7))==want
    for x,y in zip(entries,entries[1:]):
        assert ring.add(x,y)==ar.add(x,y)
        assert ring.mul(x,y)==ar.mul(x,y)


@pytest.mark.parametrize('arity',range(5))
def test_boolean_semantics(arity):
    r=ref('clause',arity,[i%2 for i in range(arity)])
    for bits in product((0,1),repeat=arity):
        assert value(r,bits)==evaluate_reference(r,bits,precision=7)==((int(any(b==i%2 for i,b in enumerate(bits))),0),)
    if arity:
        eq=ref('equality',arity,[])
        for bits in product((0,1),repeat=arity):
            assert value(eq,bits)==evaluate_reference(eq,bits,precision=7)==((int(len(set(bits))==1),0),)


def test_creation_precision_is_evaluated_before_lift():
    r=ref('packet',3,[[0],[1,2],[[[[6,0]],[[6,0]]]],[],[]])
    assert value(r,(1,1,1),5)==((4,0),)
    assert evaluate_reference(r,(1,1,1),precision=5)==((4,0),)
    wrong=ref('packet',3,[[0],[1,2],[[[[6,0]],[[6,0]]]],[],[]],p=5)
    assert value(wrong,(1,1,1),5)==((12,0),)
    with pytest.raises(ValueError):value(r,(1,1,1),2)


@pytest.mark.parametrize('seed',range(16))
def test_packet_full_unpruned_coefficient_oracle(seed):
    rng=random.Random(seed);ring=JetRing(ExtensionRing(3,7),2)
    jet=lambda:tuple(tuple(rng.randrange(8) for _ in range(2)) for _ in range(2))
    nr=seed%3;nc=seed//3%3;arity=nr+nc
    targets=[[rng.randrange(3),[jet() for _ in range(nr)]] for _ in range(seed%3)]
    sources=[[rng.randrange(3),[rng.randrange(8) for _ in range(nc)]] for _ in range(seed%2)]
    data=[list(range(nr)),list(range(nr,arity)),[[jet() for _ in range(nc)] for _ in range(nr)],targets,sources]
    r=ref('packet',arity,data,ell=2)
    for bits in product((0,1),repeat=arity):
        assert value(r,bits)==evaluate_reference(r,bits,precision=7)


@pytest.mark.parametrize('beta,expected',[(0,1),(1,0),(2,0)])
def test_empty_source_and_empty_target_conventions(beta,expected):
    r=ref('packet',0,[[],[],[],[],[[beta,[]]]])
    assert value(r,())==evaluate_reference(r,(),precision=7)==((expected,0),)
    r=ref('packet',0,[[],[],[],[[beta,[]]],[]])
    assert value(r,())==evaluate_reference(r,(),precision=7)==((expected,0),)


def test_dense_bridge_preserves_little_endian_indices():
    ring=JetRing(ExtensionRing(4,7),1)
    created=CreatedDenseTensor(3,tuple(CreationJetEntry.capture(ring,ring.elem([[i]])) for i in range(8)))
    r=source_reference_from_created(created)
    for bits in product((0,1),repeat=3):
        old=created.evaluate(bits,ring,_Budget(10000,5))
        assert value(r,bits,4)==evaluate_reference(r,bits,precision=4)==old


def test_packet_bridge_preserves_side_ids_and_noncanonical_coefficients():
    packet=PacketTensorEntry(2,(9,1,4),(('X',7),('Y',7),('X',3)),
        ((7,((7,((6,-1),)),(3,((6,2),)))),),
        ((2,1,((7,((3,-1),)),)),),((5,2,((7,-3),(3,4))),))
    created=CreatedPacketTensor(packet,3,7,2);r=source_reference_from_created(created)
    ring=JetRing(ExtensionRing(7,7),2)
    for bits in product((0,1),repeat=3):
        assert value(r,bits)==evaluate_reference(r,bits,precision=7)==created.evaluate(bits,ring,_Budget(100000,5))


@pytest.mark.parametrize('mutation',['arity','precision','f','ell','coefficient','float','bool','duplicate','extra','noncanonical','truncated'])
def test_wire_mutations_rejected(mutation):
    r=ref('dense',0,[[[1,0]]]);p=json.loads(r.description)
    if mutation=='arity':p['arity']=1
    if mutation=='precision':p['creation_precision']=4
    if mutation=='f':p['polynomial']=11
    if mutation=='ell':p['jet_length']=2
    if mutation=='coefficient':p['data'][0][0][0]=8
    if mutation=='float':p['data'][0][0][0]=1.0
    if mutation=='bool':p['data'][0][0][0]=True
    if mutation=='extra':p['unused']=0
    raw=json.dumps(p,sort_keys=True,separators=(',',':')).encode()
    if mutation=='duplicate':raw=raw.replace(b'"arity":0',b'"arity":0,"arity":0')
    if mutation=='noncanonical':raw=b' '+raw
    if mutation=='truncated':raw=raw[:-1]
    with pytest.raises(ValueError):compile_entry(replace(r,description=raw),EntryBudget(EntryLimits()))


@pytest.mark.parametrize('data',[
    [[0],[0],[[[[0,0]]]],[],[]], # overlapping ports
    [[0],[1],[],[],[]], # missing local row
    [[0],[1],[[[[0,0]]]],[[1,[]]],[]], # incomplete target support
    [[0],[1],[[[[0,0]]]],[],[[1,[-1]]]], # noncanonical source
    [[0],[1],[[[[0,0]]]],[[True,[[0,0]]]],[]],
])
def test_malformed_packet_not_treated_as_zero(data):
    with pytest.raises(ValueError):ref('packet',2,data)


@pytest.mark.parametrize('field,value_', [('max_work',0),('max_seconds',float('nan')),('max_seconds',float('inf')),('max_arity',17),('max_modes',True)])
def test_invalid_resource_policy(field,value_):
    with pytest.raises(ValueError):EntryLimits(**{field:value_})


def test_resource_caps_and_unknown_semantics():
    r=ref('dense',0,[[[1,0]]])
    with pytest.raises(SourceAdmissionError):evaluate_source_entry(r,(),precision=7,limits=EntryLimits(max_work=1))
    with pytest.raises(SourceAdmissionError):compile_entry(replace(r,recipe_kind='not-a-recipe'),EntryBudget(EntryLimits()))
    with pytest.raises(ValueError):make_reference(kind='dense',arity=100,creation_precision=3,defining_polynomial=7,jet_length=1,data=[])


def test_bridge_caps_precede_expansion():
    ring=JetRing(ExtensionRing(3,7),1)
    tensor=CreatedDenseTensor(2,tuple(CreationJetEntry.capture(ring,ring.one) for _ in range(4)))
    with pytest.raises(SourceAdmissionError):source_reference_from_created(tensor,limits=EntryLimits(max_arity=1))
    with pytest.raises(SourceAdmissionError):source_reference_from_created(tensor,limits=EntryLimits(max_coefficients=1))
    packet=CreatedPacketTensor(PacketTensorEntry(0,(),(),(),(),((0,2,()),)),3,7,1)
    with pytest.raises(SourceAdmissionError):source_reference_from_created(packet,limits=EntryLimits(max_exponent=1))

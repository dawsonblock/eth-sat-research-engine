import copy
import itertools
import random
import pytest
from veritas.research.eth_packing.parameters import manuscript_parameters,scaled_parameters
from veritas.research.eth_packing.labels import assign_endpoint_labels
from veritas.research.eth_packing.packing import construct_packing,PackingLimit
from veritas.research.eth_packing.checker import check_packing
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials,verify_cauchy_matrix,evaluate
from veritas.research.eth_arithmetic.gf2 import degree,is_irreducible,first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing


def test_parameters_exact_vs_scaled():
    p=manuscript_parameters(1000)
    assert p.mode=='MANUSCRIPT_EXACT' and not p.eligible and p.u==0
    assert not manuscript_parameters(1<<131072).eligible  # M, delta were not supplied
    assert not scaled_parameters(1000).theorem_parameters
    assert manuscript_parameters(1<<131072,depth=1).u==0

@pytest.mark.parametrize('e',range(1,11))
def test_irreducible_generated(e):
    f=first_irreducible(e)
    assert degree(f)==e and is_irreducible(f)
    if e>1:
        assert not is_irreducible((1<<e)|1) if e%2==0 else True

@pytest.mark.parametrize('precision', [1,2,3,8,16])
@pytest.mark.parametrize('degree', [1,2,3,4,6])
def test_extension_ring_randomized(precision,degree):
    rng=random.Random(1000+precision*10+degree)
    R=ExtensionRing(precision,first_irreducible(degree))
    for _ in range(30):
        a=R.elem([rng.randrange(R.modulus) for _ in range(degree)])
        b=R.elem([rng.randrange(R.modulus) for _ in range(degree)])
        c=R.elem([rng.randrange(R.modulus) for _ in range(degree)])
        assert R.mul(a,b)==R.mul(b,a)
        assert R.mul(R.mul(a,b),c)==R.mul(a,R.mul(b,c))
        assert R.mul(a,R.one)==a
        assert R.mul(a,R.add(b,c))==R.add(R.mul(a,b),R.mul(a,c))
        if R.is_unit(a): assert R.mul(a,R.inverse(a))==R.one
        else:
            with pytest.raises(ZeroDivisionError): R.inverse(a)

@pytest.mark.parametrize('jetlen',[1,2,4,6])
def test_jet_ring_inverse(jetlen):
    rng=random.Random(jetlen)
    R=ExtensionRing(9,first_irreducible(4));J=JetRing(R,jetlen)
    for _ in range(20):
        a=[R.elem([rng.randrange(512) for _ in range(4)]) for _ in range(jetlen)]
        if not R.is_unit(a[0]):a[0]=R.one
        a=tuple(a)
        assert J.mul(a,J.inverse(a))==J.one

@pytest.mark.parametrize('L',[1,2,3,4,5,8,12,16])
def test_cauchy_matrix(L):
    assert verify_cauchy_matrix(L)
    m=cauchy_matrix_polynomials(L)
    for t in range(-L,L):
        for x in range(L):
            for y in range(L):
                if t!=y-x:
                    assert evaluate(m[x][y],t)==0


def test_exact_packing_valid_fixture():
    # Choose all 2^a orientation slots per class once.
    edges=[(i,i+4) for i in range(4)]
    labels={i: ((i&1),((i>>1)&1)) for i in range(4)}
    labels.update({i+4: (1-(i&1), 1-((i>>1)&1)) for i in range(4)})
    cert=construct_packing(edges,r=2,a=2,labels=labels,enforce_bounds=True)
    assert len(cert['packets'])==1
    assert cert['verification']['all_bounds_satisfied']
    assert check_packing(cert,require_bounds=True)['all_bounds_satisfied']
    for mutation in ['duplicate','missing','flip','labels','padding']:
        bad=copy.deepcopy(cert)
        if mutation=='duplicate':bad['packets'][0]['slots'][0]=bad['packets'][0]['slots'][1]
        if mutation=='missing':bad['packets'][0]['slots'][0]=None
        if mutation=='flip':bad['packets'][0]['symbol_pairs'][0][0]=1
        if mutation=='labels':bad['labels']['0'][0]=1
        if mutation=='padding':bad['packets'][0]['slots'].append(None)
        assert not check_packing(bad)['valid_structure']


def test_packing_rejects_false_bounds():
    cert=construct_packing([(0,1)],r=4,a=3)
    assert cert['verification']['valid_structure']
    assert not cert['verification']['all_bounds_satisfied']
    with pytest.raises(PackingLimit):
        construct_packing([(0,1)],r=4,a=3,enforce_bounds=True)


def test_random_packet_structure_and_independent_checker():
    rng=random.Random(44)
    for _ in range(150):
        v=rng.randrange(2,10)
        edges=[(rng.randrange(v),rng.randrange(v)) for _ in range(rng.randrange(1,40))]
        cert=construct_packing(edges,r=rng.choice([2,3,4]),a=rng.choice([1,2,3]))
        assert check_packing(cert)['valid_structure']
        labels=assign_endpoint_labels(edges,r=4,a=2)
        assert all(len(x)==2 for x in labels.values())

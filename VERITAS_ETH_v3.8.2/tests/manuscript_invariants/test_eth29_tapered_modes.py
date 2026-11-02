"""M3/M4 finite exact tests; no claim about asymptotic D.4.4 recursion."""
from copy import deepcopy
from fractions import Fraction
from random import Random
import pytest
from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan,sample_integer_polynomial,reconstruct_tapered,
    check_tapered_against_polynomial)
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_modes_v29.extension_modes import make_extension_modes,check_extension_modes
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.extension_lagrange import evaluate_polynomial
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry

@pytest.mark.parametrize('M,a,u,p',[(1,1,1,3),(2,1,1,8),(3,1,1,10),
                                  (4,1,1,7),(1,2,1,7),(2,2,1,12)])
def test_tapered_recovery_randomized(M,a,u,p):
    plan=make_tapered_plan(M=M,a=a,u=u,p=p)
    assert plan.degree_bound==M*((2<<a)-1)
    assert sum(x.multiplicity for x in plan.nodes)>plan.degree_bound
    assert all(x.precision_bits>=dict(plan.necessary_precision)[x.t] for x in plan.nodes)
    rng=Random(777+M*100+a*10+p)
    for _ in range(16):
        poly=[rng.randint(-1000,1000) for j in range(plan.degree_bound+1)]
        samples=sample_integer_polynomial(plan,poly)
        assert reconstruct_tapered(plan,samples)==poly[0]%(1<<p)
        assert check_tapered_against_polynomial(plan,samples,poly)['valid']
        first=plan.nodes[0]
        modified=dict(samples)
        vals=list(modified[first.t]);vals[0]=(vals[0]+1)%(1<<first.precision_bits)
        modified[first.t]=tuple(vals)
        assert not check_tapered_against_polynomial(plan,modified,poly)['valid']


def test_tapered_fail_closed_and_2adic_guard():
    p=make_tapered_plan(M=2,a=1,u=1,p=8)
    samples=sample_integer_polynomial(p,[3,1,-5,2])
    with pytest.raises(ValueError,match='missing'):
        reconstruct_tapered(p,{})
    bad=deepcopy(samples);node=p.nodes[0];bad[node.t]=(-1,)+bad[node.t][1:]
    with pytest.raises(ValueError,match='outside'):
        reconstruct_tapered(p,bad)
    with pytest.raises(ValueError,match='degree'):
        make_tapered_plan(M=7,a=2,u=1,p=8)
    with pytest.raises(ValueError,match='budget'):
        make_tapered_plan(M=2,a=1,u=1,p=8,max_degree=1) # budget rejection instead
    with pytest.raises(ValueError,match='u <= a'):
        make_tapered_plan(M=2,a=1,u=2,p=8)
    with pytest.raises(ValueError,match='u <= M'):
        make_tapered_plan(M=1,a=2,u=2,p=8)


def test_explicit_extended_target_precision_preserves_exact_reconstruction():
    with pytest.raises(ValueError, match='bounded range'):
        make_tapered_plan(M=1, a=1, u=1, p=131)
    plan = make_tapered_plan(M=1, a=1, u=1, p=131,
                             max_target_precision=512, max_work_precision=1024)
    polynomial = [-5, 17, -23, 9]
    samples = sample_integer_polynomial(plan, polynomial)
    assert reconstruct_tapered(plan, samples) == polynomial[0] % (1 << 131)
    assert all(node.precision_bits <= 1024 for node in plan.nodes)


@pytest.mark.parametrize('edges',[
    [[0,0],[1,1],[0,1],[1,0]],
    [[0,0],[0,1],[1,0],[1,1]],
    [[0,0],[0,0],[1,1],[1,1]],
    [[0,1],[1,0],[0,0],[1,1],[1,1]],
])
@pytest.mark.parametrize('precision,degree,length',[(3,2,1),(5,3,2),(8,4,3),(11,4,4)])
def test_extension_mode_reconstruction(edges,precision,degree,length):
    c=construct_d3_packing(edges,r=2,a=1)
    z=make_extension_modes(c,node=1,precision=precision,extension_degree=degree,jet_length=length)
    result=check_extension_modes(z)
    assert result['valid'],result
    assert result['recursive_child_networks'] is False
    assert not result['manuscript_geometric_modes']
    # Each returned mode's reported valuation is the actual minimum
    ring=ExtensionRing(precision,first_irreducible(degree))
    for mode in z['modes']:
        assert min(ring.valuation(tuple(coeff)) for _,jet in mode['rows'] for coeff in jet)==mode['weight']
    if z['modes']:
        forged=deepcopy(z)
        mode=forged['modes'][0]
        mode['rows'][0][1][0][0]=(mode['rows'][0][1][0][0]+1)%(1<<precision)
        assert not check_extension_modes(forged)['valid']
        missing=deepcopy(z);missing['modes'].pop()
        assert not check_extension_modes(missing)['valid']


def test_extension_cauchy_jet_evaluation_has_independent_full_polynomial_oracle():
    ring=ExtensionRing(9,first_irreducible(4))
    for x in range(2):
        for y in range(2):
            original=shift_cauchy_entry(2,1,ring,x,y)
            for z in [ring.zero,ring.one,ring.elem([1,0,1]),ring.elem([0,1])]:
                val=evaluate_polynomial(ring,original,z)
                assert len(val)==ring.e


def test_mode_rejects_tampering_and_invalid_parameters():
    c=construct_d3_packing([[0,0],[1,1],[0,1],[1,0]],r=2,a=1)
    cert=make_extension_modes(c)
    bad=deepcopy(cert);bad['scope']['subexponential_runtime_proven']=True
    assert not check_extension_modes(bad)['valid']
    bad=deepcopy(cert);bad['cross_pairs'].pop()
    assert not check_extension_modes(bad)['valid']
    bad=deepcopy(cert);bad['irreducible_polynomial']=9999
    assert not check_extension_modes(bad)['valid']
    with pytest.raises(ValueError):make_extension_modes(c,precision=0)
    with pytest.raises(ValueError):make_extension_modes(c,jet_length=15)

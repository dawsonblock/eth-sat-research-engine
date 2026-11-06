"""Seeded finite reference validation; not a proof of the ETH theorem."""
from __future__ import annotations
import json,sys
from pathlib import Path
from random import Random
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan,sample_integer_polynomial,reconstruct_tapered,
    check_tapered_against_polynomial)
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_modes_v29.extension_modes import make_extension_modes,check_extension_modes
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_interpolation.extension_lagrange import evaluate_polynomial
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials, evaluate
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry

rng=Random(20261031)
poly_checks=0
for M,a,u,p in [(1,1,1,5),(2,1,1,8),(3,1,1,9),(2,2,1,11)]:
    plan=make_tapered_plan(M=M,a=a,u=u,p=p)
    for _ in range(60):
        coeff=[rng.randrange(-500,501) for _ in range(plan.degree_bound+1)]
        jets=sample_integer_polynomial(plan,coeff)
        assert reconstruct_tapered(plan,jets)==coeff[0]%(1<<p)
        assert check_tapered_against_polynomial(plan,jets,coeff)['valid']
        poly_checks+=1
mode_checks=0
for n in range(3,9):
    for _ in range(12):
        edges=[[rng.randrange(3),rng.randrange(3)] for _ in range(n)]
        d3=construct_d3_packing(edges,r=2,a=1)
        for p in (3,8):
            for length in (1,3):
                m=make_extension_modes(d3,node=1,precision=p,extension_degree=4,jet_length=length)
                status=check_extension_modes(m)
                assert status['valid'],status
                mode_checks+=1
# Independent direct rational scalar evaluations of shifted W for extension
# test points in the base subring, across interpolation centres.
scalar_checks=0
for L in (2,4):
    r=ExtensionRing(12,first_irreducible(4))
    alpha=2*L
    coeff=cauchy_matrix_polynomials(L)
    for t in range(-L,L):
        for x in range(L):
            for y in range(L):
                jet=shift_cauchy_entry(L,t,r,x,y)
                for z in (-2,-1,0,1,2):
                    got=evaluate_polynomial(r,jet,r.elem([z]))
                    expected=evaluate(coeff[x][y],t+alpha*z)
                    assert expected.denominator%2==1
                    residue=expected.numerator*pow(expected.denominator,-1,1<<r.p)%(1<<r.p)
                    assert got==r.elem([residue])
                    scalar_checks+=1
print(json.dumps({'status':'PASS','seed':20261031,
    'tapered_integer_polynomial_exact_cases':poly_checks,
    'extension_mode_certificate_cases':mode_checks,
    'independent_rational_Cauchy_entry_checks':scalar_checks,
    'claims_not_established':['D.4.4 geometric tile expansion over full extension ring',
        'implicit recursive child contraction','subexponential runtime']},indent=2))

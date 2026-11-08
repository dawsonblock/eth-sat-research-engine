"""Seeded independent Cauchy kernel / jet validation; zero tolerance."""
from __future__ import annotations
import json
from pathlib import Path
from fractions import Fraction
from random import Random
from time import monotonic
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_deformation import (
    exact_cauchy_deformation, verify_cauchy_small, shifted_cauchy_jet_mod,
    _polynomial_shift, shifted_integral_kernel)


def modp(f, p):
    f=Fraction(f)
    if f.denominator%2==0:
        raise AssertionError('even denominator in supposedly integral shifted polynomial')
    return (f.numerator*pow(f.denominator,-1,1<<p)) % (1<<p)


def run():
    start=monotonic()
    rng=Random(26081029)
    checks=0
    shifted_checks=0
    for L in (1,2,4,8):
        for t in range(-L,L):
            mat=shifted_integral_kernel(L,t)
            assert all(v.denominator%2 for row in mat for coeff in row for v in coeff)
            checks+=1
    count=0
    for trial in range(180):
        n=rng.randint(0,5)
        m=rng.randint(0,4)
        clauses=[]
        for _ in range(m):
            k=rng.randint(0,2) if n else 0
            clauses.append([rng.choice((-1,1))*rng.randint(1,n) for _ in range(k)])
        M=sum(len(c) for c in clauses)
        if M>5:
            continue
        cnf=CNF.from_lists(n,clauses)
        net=from_cnf(cnf,max_degree=6)
        L=rng.choice((1,2,4))
        poly, _=exact_cauchy_deformation(net,packet_size=L,max_edges=5,timeout_s=5)
        node_checks=verify_cauchy_small(net,poly,L,timeout_s=5)
        assert len(node_checks['grid_nodes_checked'])==2*L
        count+=1
        checks+=2*L+1
        for _ in range(3):
            t=rng.randrange(-L,L)
            p=rng.randrange(1,18)
            order=rng.randrange(1, min(9, M*(2*L-1)+4))
            jet, _=shifted_cauchy_jet_mod(net,packet_size=L,node=t,
                            precision_bits=p,jet_order=order,max_edges=5,timeout_s=5)
            oracle=_polynomial_shift(poly,t,2*L,order)
            assert jet==tuple(modp(oracle[j] if j<len(oracle) else 0,p) for j in range(order))
            shifted_checks+=1
    summary={
        'version':'0.8.0',
        'status':'PASS',
        'seed':26081029,
        'local_kernel_2adic_integrality_grid_checks':sum(2*L for L in (1,2,4,8)),
        'randomized_cnf_networks_checked':count,
        'grid_invariant_checks_including_randomized':checks,
        'independent_shifted_jets_checked':shifted_checks,
        'max_original_wire_budget':5,
        'max_packet_size':8,
        'elapsed_s':round(monotonic()-start,3),
        'claim':'small finite test evidence only; no ETH runtime theorem or recursive algorithm'
    }
    out=Path(__file__).resolve().parents[1]/'validation/validation_v08.json'
    out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':run()

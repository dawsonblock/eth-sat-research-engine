"""Deterministic randomized finite packing and 2-adic arithmetic checks.

This reports tested-instance correctness, never a proof of a global theorem.
"""
import random
from veritas.research.eth_packing.packing import construct_packing
from veritas.research.eth_packing.checker import check_packing
from veritas.research.eth_packing.cauchy import verify_cauchy_matrix
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing

rng = random.Random(250025)
packing_checked=0
ring_checked=0
for _ in range(600):
    n=rng.randrange(2,15)
    edges=[(rng.randrange(n),rng.randrange(n)) for _ in range(rng.randrange(1,65))]
    p=construct_packing(edges,r=rng.randint(2,6),a=rng.randint(1,3))
    assert check_packing(p)['valid_structure']
    packing_checked+=1
for _ in range(400):
    d=rng.choice([1,2,3,4,5,6,8]);precision=rng.choice([1,2,4,8,16])
    R=ExtensionRing(precision,first_irreducible(d))
    a=R.elem([rng.randrange(R.modulus) for _ in range(d)])
    b=R.elem([rng.randrange(R.modulus) for _ in range(d)])
    assert R.mul(a,b)==R.mul(b,a)
    if R.is_unit(a):assert R.mul(a,R.inverse(a))==R.one
    ring_checked+=1
assert all(verify_cauchy_matrix(s) for s in (1,2,4,8,16))
print({'packings_checked':packing_checked,'ring_cases_checked':ring_checked,
       'cauchy_sizes_checked':5,'status':'PASS',
       'scope':'finite exact invariants only; no ETH complexity claim'})

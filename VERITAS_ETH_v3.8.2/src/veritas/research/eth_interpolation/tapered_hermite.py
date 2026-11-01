"""Bounded valuation-tapered Hermite reconstruction over Z/2**p.

M3 FINITE REFERENCE ONLY. The *formulas* for q_t and p_t follow the
manuscript schedule, but the implementation uses a small rational confluent
system instead of the manuscript's asymptotically efficient algorithm.
Mixed-precision inputs are accepted ONLY after checking exact coefficient-wise
precision requirements. No division by a nonunit occurs in the residue ring.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from math import comb
from veritas.research.hermite_ring import hermite_plan


def v2_integer(n: int) -> int:
    if not n:
        raise ValueError('v2(0) is not finite')
    k=abs(n)
    return (k & -k).bit_length()-1


def v2_fraction(x: Fraction) -> int:
    if not x:
        return 10**9
    return v2_integer(x.numerator)-v2_integer(x.denominator)


@dataclass(frozen=True)
class TaperedNode:
    t: int
    valuation: int
    multiplicity: int
    precision_bits: int


@dataclass(frozen=True)
class TaperedPlan:
    packets_exponent: int
    wires: int
    u: int
    target_bits: int
    alpha: int
    degree_bound: int
    nodes: tuple[TaperedNode, ...]
    recovery_plan: object
    necessary_precision: tuple[tuple[int,int], ...]
    claim: str = 'FINITE_TAPERED_HERMITE_REFERENCE_ONLY'

    def to_dict(self):
        return {'claim':self.claim,'a':self.packets_exponent,'M':self.wires,
            'u':self.u,'target_bits':self.target_bits,'alpha':self.alpha,
            'degree_bound':self.degree_bound,'guard_bits':self.recovery_plan.guard_bits,
            'nodes':[vars(x) for x in self.nodes],
            'required_input_bits_by_node':[list(x) for x in self.necessary_precision],
            'source_matched_asymptotic_algorithm':False,
            'subexponential_runtime_proven':False}


def make_tapered_plan(*, M:int, a:int, u:int, p:int, max_degree=31,
                      max_nodes=32, max_work_precision=4096) -> TaperedPlan:
    if any(type(x) is not int for x in (M,a,u,p,max_degree,max_nodes,max_work_precision)):
        raise ValueError('integer parameters required')
    if not 1<=M<=32 or not 1<=a<=5 or not 1<=u<=16 or not 1<=p<=128:
        raise ValueError('finite reference parameters outside bounded range')
    if u > a or u > M:
        raise ValueError('tapered lemma requires 1 <= u <= a and u <= M')
    L=1<<a;deg=M*(2*L-1)
    if deg>min(max_degree,31) or 2*L>max_nodes:
        raise ValueError('degree or node count exceeds the exact reference budget')
    h=(3*M+u-1)//u
    nodes=[]
    for t in range(-L,L):
        if t==0:continue
        i=v2_integer(t)
        q=h*max(0,u-i)
        if q:
            prec=p+8*h*(L//(1<<i))+8*M*(a+1)
            if prec>max_work_precision:
                raise ValueError('manuscript guard precision exceeds reference budget')
            nodes.append(TaperedNode(t,i,q,prec))
    if not nodes or sum(x.multiplicity for x in nodes)<=deg:
        raise ValueError('tapered node multiplicity does not exceed polynomial degree')
    # Confluent basis only needs deg+1 coefficients, never artificially use
    # more than that in the small exact rational solve.
    specs=[(x.t,min(x.multiplicity,deg+1)) for x in nodes]
    rec=hermite_plan(specs,alpha=1<<(a+1),degree_bound=deg)
    requirements={x.t:0 for x in nodes}
    for (t,j),w in zip(rec.samples_used,rec.weights):
        if w:
            requirements[t]=max(requirements[t],p-v2_fraction(w))
    for x in nodes:
        if x.precision_bits<requirements[x.t]:
            raise ValueError(f'node {x.t} lacks required input precision')
    return TaperedPlan(a,M,u,p,1<<(a+1),deg,tuple(nodes),rec,
                       tuple((x.t,requirements[x.t]) for x in nodes))


def _fraction_mod_odd(x:Fraction,bits:int):
    if x.denominator%2==0:
        raise ValueError('nonunit denominator after certified scaling')
    m=1<<bits
    return x.numerator*pow(x.denominator,-1,m)%m


def reconstruct_tapered(plan:TaperedPlan, jets:dict[int,tuple[int,...]]) -> int:
    """Jet samples stored at their INDIVIDUAL prescribed node precisions."""
    rec=plan.recovery_plan
    if not isinstance(jets,dict) or set(jets)!={x.t for x in plan.nodes}:
        raise ValueError('missing, extra or duplicate tapered node')
    for node in plan.nodes:
        values=jets[node.t]
        if len(values)<min(node.multiplicity,plan.degree_bound+1):
            raise ValueError(f'insufficient coefficients at node {node.t}')
        if any(type(v) is not int or v<0 or v>=1<<node.precision_bits
               for v in values[:min(node.multiplicity,plan.degree_bound+1)]):
            raise ValueError('jet residue outside its declared precision')
    shift=rec.guard_bits
    modulus_bits=plan.target_bits+shift
    accumulator=0
    scale=1<<shift
    for (t,j),w in zip(rec.samples_used,rec.weights):
        coefficient=Fraction(w)*scale
        if coefficient.denominator%2==0:
            raise ArithmeticError('Hermite guard scaling did not clear 2-denominator')
        node=next(x for x in plan.nodes if x.t==t)
        required=plan.target_bits-v2_fraction(w)
        if node.precision_bits<required:
            raise ValueError('insufficient coefficient-dependent input precision')
        c=_fraction_mod_odd(coefficient,modulus_bits)
        accumulator=(accumulator+c*jets[t][j])%(1<<modulus_bits)
    if accumulator%scale:
        raise ValueError('incompatible jets: reconstruction not integral')
    return (accumulator//scale)%(1<<plan.target_bits)


def sample_integer_polynomial(plan:TaperedPlan,coefficients):
    """Independent exact rational expansion oracle for small bounded tests."""
    coeff=tuple(Fraction(v) for v in coefficients)
    if len(coeff)>plan.degree_bound+1:
        raise ValueError('polynomial exceeds degree bound')
    out={}
    for node in plan.nodes:
        values=[]
        for j in range(min(node.multiplicity,plan.degree_bound+1)):
            exact=sum((c*comb(k,j)*node.t**(k-j)*plan.alpha**j
                       for k,c in enumerate(coeff) if k>=j),Fraction(0))
            values.append(_fraction_mod_odd(exact,node.precision_bits))
        out[node.t]=tuple(values)
    return out


def check_tapered_against_polynomial(plan:TaperedPlan,jets,coefficients):
    """Oracle-backed check, not a self-contained proof of arbitrary jet data."""
    reference=sample_integer_polynomial(plan,coefficients)
    for t,values in reference.items():
        if t not in jets or tuple(jets[t][:len(values)])!=values:
            return {'valid':False,'reason':f'jet mismatch at node {t}'}
    expected=_fraction_mod_odd(Fraction(coefficients[0]),plan.target_bits)
    actual=reconstruct_tapered(plan,jets)
    return {'valid':actual==expected,'expected':expected,'recovered':actual,
            'scope':plan.claim,'independent_source_polynomial_required':True}

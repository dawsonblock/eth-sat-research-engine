"""Bounded valuation-tapered Hermite reconstruction over Z/2**p.

M3 FINITE REFERENCE ONLY. The *formulas* for h, q_t and p_t follow
`lem:tapered-hermite` in `app:tensor` of the pinned preprint, but the
implementation uses a small rational confluent system instead of the paper's
asymptotically efficient algorithm.
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
                      max_nodes=32, max_work_precision=4096,
                      max_target_precision=128) -> TaperedPlan:
    if any(type(x) is not int for x in (M,a,u,p,max_degree,max_nodes,max_work_precision,max_target_precision)):
        raise ValueError('integer parameters required')
    if (not 1 <= max_target_precision <= 1024 or
            not 1<=M<=32 or not 1<=a<=5 or not 1<=u<=16 or not 1<=p<=max_target_precision):
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


def validate_tapered_plan(plan: TaperedPlan) -> None:
    """Independently check one finite schedule and recovery functional.

    This checks the pinned formulas and evaluates the proposed exact linear
    functional on every monomial in the permitted polynomial space. It is a
    bounded finite verifier, not a proof of the global tapering lemma or of
    the algorithm's asymptotic complexity. It raises ``ValueError`` on an
    inconsistent plan instead of attempting reconstruction.
    """
    if not isinstance(plan, TaperedPlan):
        raise ValueError('finite tapered plan required')
    M,a,u,p = plan.wires,plan.packets_exponent,plan.u,plan.target_bits
    if (any(type(x) is not int for x in (M,a,u,p,plan.alpha,plan.degree_bound)) or
            not 1<=M<=32 or not 1<=a<=5 or not 1<=u<=min(a,M) or
            not 1<=p<=1024 or plan.claim!='FINITE_TAPERED_HERMITE_REFERENCE_ONLY'):
        raise ValueError('invalid finite tapered plan parameters')
    L=1<<a
    degree=M*(2*L-1)
    if degree>31 or plan.degree_bound!=degree or plan.alpha!=2*L:
        raise ValueError('tapered degree or interpolation scale is incorrect')
    h=(3*M+u-1)//u
    expected_nodes=[]
    for t in range(-L,L):
        if not t:
            continue
        i=v2_integer(t)
        if i<u:
            expected_nodes.append(TaperedNode(t,i,h*(u-i),
                p+8*h*(L>>i)+8*M*(a+1)))
    if (type(plan.nodes) is not tuple or plan.nodes!=tuple(expected_nodes) or
            not expected_nodes or sum(n.multiplicity for n in expected_nodes)<=degree):
        raise ValueError('tapered nodes or prescribed precision are incorrect')
    rec=plan.recovery_plan
    specs=tuple((node.t,min(node.multiplicity,degree+1)) for node in expected_nodes)
    samples=tuple((t,j) for t,m in specs for j in range(m))[:degree+1]
    if (getattr(rec,'nodes',None)!=specs or getattr(rec,'alpha',None)!=plan.alpha or
            getattr(rec,'degree_bound',None)!=degree or
            getattr(rec,'samples_used',None)!=samples or
            type(getattr(rec,'weights',None)) is not tuple or len(rec.weights)!=degree+1):
        raise ValueError('Hermite recovery description is inconsistent')
    if any(not isinstance(w,Fraction) or w.numerator.bit_length()>16384 or
           w.denominator.bit_length()>16384 for w in rec.weights):
        raise ValueError('invalid or oversized exact recovery weight')
    for k in range(degree+1):
        value=sum((w*comb(k,j)*t**(k-j)*plan.alpha**j
                   for (t,j),w in zip(samples,rec.weights) if j<=k),Fraction(0))
        if value!=(1 if k==0 else 0):
            raise ValueError('Hermite weights do not recover the original value')
    guard=max((max(0,-v2_fraction(w)) for w in rec.weights if w),default=0)
    if type(getattr(rec,'guard_bits',None)) is not int or rec.guard_bits!=guard:
        raise ValueError('Hermite guard is inconsistent with exact weights')
    required={node.t:0 for node in expected_nodes}
    for (t,_),w in zip(samples,rec.weights):
        if w:
            required[t]=max(required[t],p-v2_fraction(w))
    if (plan.necessary_precision!=tuple((n.t,required[n.t]) for n in expected_nodes) or
            any(n.precision_bits<required[n.t] for n in expected_nodes)):
        raise ValueError('tapered coefficient precision requirements are inconsistent')


def _fraction_mod_odd(x:Fraction,bits:int):
    if x.denominator%2==0:
        raise ValueError('nonunit denominator after certified scaling')
    m=1<<bits
    return x.numerator*pow(x.denominator,-1,m)%m


def reconstruct_tapered(plan:TaperedPlan, jets:dict[int,tuple[int,...]], *,
                        coefficient_precisions=None) -> int:
    """Recover a residue from explicitly bounded-precision jet coefficients.

    With no metadata, every coefficient is declared to have its node's
    prescribed precision, as in the original interface. When supplied,
    ``coefficient_precisions[t][j]`` declares the actual precision of that
    coefficient; zero bits means the unique residue modulo one. The caller
    remains responsible for obtaining each residue at its declared precision.
    """
    validate_tapered_plan(plan)
    return _reconstruct_tapered_validated(plan, jets, coefficient_precisions=coefficient_precisions)


def _reconstruct_tapered_validated(plan:TaperedPlan, jets:dict[int,tuple[int,...]], *,
                                   coefficient_precisions=None) -> int:
    """Internal fast path: caller must validate this exact immutable plan."""
    rec=plan.recovery_plan
    if (not isinstance(jets,dict) or any(type(t) is not int for t in jets) or
            set(jets)!={x.t for x in plan.nodes}):
        raise ValueError('missing, extra or duplicate tapered node')
    if coefficient_precisions is not None and (
            not isinstance(coefficient_precisions, dict) or
            any(type(t) is not int for t in coefficient_precisions) or
            set(coefficient_precisions) != {x.t for x in plan.nodes}):
        raise ValueError('precision metadata must cover exactly the tapered nodes')
    actual_precisions={}
    for node in plan.nodes:
        values=jets[node.t]
        count=min(node.multiplicity,plan.degree_bound+1)
        if not isinstance(values,(tuple,list)) or len(values)<count:
            raise ValueError(f'insufficient coefficients at node {node.t}')
        if coefficient_precisions is None:
            precisions=(node.precision_bits,)*count
        else:
            precisions=coefficient_precisions[node.t]
            if (not isinstance(precisions,(tuple,list)) or len(precisions)<count or
                    any(type(bits) is not int or not 0<=bits<=node.precision_bits
                        for bits in precisions[:count])):
                raise ValueError('invalid coefficient precision metadata')
        if any(type(v) is not int or v<0 or v>=1<<bits
               for v,bits in zip(values[:count],precisions[:count])):
            raise ValueError('jet residue outside its declared precision')
        actual_precisions[node.t]=precisions
    shift=rec.guard_bits
    modulus_bits=plan.target_bits+shift
    accumulator=0
    scale=1<<shift
    for (t,j),w in zip(rec.samples_used,rec.weights):
        coefficient=Fraction(w)*scale
        if coefficient.denominator%2==0:
            raise ArithmeticError('Hermite guard scaling did not clear 2-denominator')
        required=max(0,plan.target_bits-v2_fraction(w)) if w else 0
        if actual_precisions[t][j]<required:
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

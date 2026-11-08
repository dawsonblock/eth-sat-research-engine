"""Full node-specific Hermite reconstruction in the creation coefficient ring."""
from fractions import Fraction
from dataclasses import replace
from .parameters import hermite_nodes
from .ring import Ring


def functional(node,nodes,alpha,degree,budget):
    """eq:tensor-hermite-origin, one node's reciprocal series at a time."""
    q=node.multiplicity;budget.items(q,'Hermite reciprocal series')
    inverse=[Fraction(1)]+[Fraction(0)]*(q-1);at_zero=Fraction(1)
    for other in nodes:
        if other.t==node.t:continue
        delta=node.t-other.t
        at_zero*=Fraction(-other.t,delta)**other.multiplicity
        ratio=Fraction(alpha,delta);factor=[Fraction(1)]
        for k in range(1,q):
            budget.tick();factor.append(-factor[-1]*ratio*Fraction(other.multiplicity+k-1,k))
        combined=[Fraction(0)]*q
        for i,left in enumerate(inverse):
            if left:
                for k in range(q-i):budget.tick();combined[i+k]+=left*factor[k]
        inverse=combined
    x=Fraction(-node.t,alpha);weights=[]
    for j in range(min(q,degree+1)):
        value=Fraction(0)
        # Horner evaluation avoids separately recomputing every rational power.
        for coefficient in reversed(inverse[:q-j]):
            budget.tick();value=value*x+coefficient
        weights.append(at_zero*x**j*value)
    return tuple(weights)


def evaluate_scalar(polynomial,x,ring):
    out=ring.zero_scalar
    for c in reversed(polynomial):out=ring.scalar_add(ring.scalar_mul(out,x),c)
    return out


def interpolate_values(degree,ring,evaluate):
    """Online Newton interpolation at all d+1 binary-coordinate lifts."""
    if degree+1>1 << ring.e:raise ValueError('insufficient residue-field interpolation capacity')
    ring.budget.items((degree+2)*ring.e*(ring.ell+1),'interpolation state')
    polynomial=[];basis=[ring.one_scalar]
    for index in range(degree+1):
        ring.budget.tick();x=tuple((index >> j)&1 for j in range(ring.e))
        value=ring.canonical(evaluate(x))
        old=ring.zero
        for c in reversed(polynomial):old=ring.add(ring.scale(old,x),c)
        denominator=evaluate_scalar(basis,x,ring)
        coefficient=ring.scale(ring.sub(value,old),ring.inverse(denominator))
        polynomial.append(ring.zero)
        polynomial=[ring.add(c,ring.scale(coefficient,b)) for c,b in zip(polynomial,basis)]
        next_basis=[ring.zero_scalar]*(len(basis)+1)
        for j,b in enumerate(basis):
            next_basis[j]=ring.scalar_sub(next_basis[j],ring.scalar_mul(x,b))
            next_basis[j+1]=ring.scalar_add(next_basis[j+1],b)
        basis=next_basis
    return tuple(polynomial)


def recover(M,a,u,target_ring,evaluate_point,*,experimental_precision=False):
    """Obtain every required local polynomial and reconstruct F(0).

    evaluate_point receives (node, binary lift, node Ring). All derivative and
    V coefficients retain the node's own prescribed p_t; no common-precision
    or constant-degree experimental schedule is substituted.
    """
    budget=target_ring.budget;L=1 << a;degree=M*(2*L-1)
    budget.items(2*L,'Hermite node inventory')
    nodes=tuple(hermite_nodes(M,a,u,target_ring.p))
    if sum(n.multiplicity for n in nodes)<=degree:raise ArithmeticError('insufficient Hermite multiplicity')
    if experimental_precision:
        # Explicit finite-experiment policy only. Each supplied local value is
        # known modulo 2**p_t. These rational linear-functional coefficients
        # prove p_t >= root_p + max v2(denominator) is sufficient for F(0).
        # Multiplicities, interpolation degree and every node stay unchanged.
        nodes=tuple(replace(node,precision=target_ring.p+max(
            (w.denominator & -w.denominator).bit_length()-1
            for w in functional(node,nodes,2*L,degree,budget))) for node in nodes)
    totals=[[Fraction(0) for _ in range(target_ring.e)] for _ in range(target_ring.ell)]
    for node in nodes:
        weights=functional(node,nodes,2*L,degree,budget)
        for weight in weights:
            loss=(weight.denominator&-weight.denominator).bit_length()-1
            if node.precision<target_ring.p+loss:raise ArithmeticError('tapered precision is insufficient')
        ring=Ring(node.precision,target_ring.f,target_ring.ell,budget)
        polynomial=interpolate_values(degree,ring,lambda z:evaluate_point(node,z,ring))
        for coefficient,weight in zip(polynomial,weights):
            for j,row in enumerate(coefficient):
                for k,value in enumerate(row):
                    budget.tick();totals[j][k]+=weight*value
                    budget.bits(totals[j][k].numerator.bit_length()+totals[j][k].denominator.bit_length(),'Hermite rational coordinate')
    output=[];modulus=1 << target_ring.p
    for row in totals:
        out=[]
        for value in row:
            if not value.denominator&1:raise ArithmeticError('nonintegral reconstructed contraction')
            out.append(value.numerator*pow(value.denominator,-1,modulus)%modulus)
        output.append(tuple(out))
    return tuple(output)

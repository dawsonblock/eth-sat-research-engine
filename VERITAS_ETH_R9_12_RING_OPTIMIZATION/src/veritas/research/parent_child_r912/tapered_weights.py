"""General node-specific manuscript functional and independent series inverse."""
from fractions import Fraction
from math import comb


def reference_prefix(nodes, alpha, degree, budget):
    """Build E_t first, then invert by coefficient recurrence (not factor reciprocals)."""
    answer=[]
    for node in nodes:
        order=node.multiplicity
        polynomial=[Fraction(1)]+[Fraction(0)]*(order-1)
        at_zero=Fraction(1)
        for other in nodes:
            if other.t==node.t:
                continue
            delta=node.t-other.t
            at_zero*=Fraction(-other.t,delta)**other.multiplicity
            factor=[Fraction(comb(other.multiplicity,k))*Fraction(alpha,delta)**k
                    for k in range(min(order,other.multiplicity+1))]
            polynomial=[sum((polynomial[j-k]*factor[k] for k in range(min(j+1,len(factor)))),Fraction(0))
                        for j in range(order)]
            budget.tick(order*len(factor))
        inverse=[Fraction(1)]
        for j in range(1,order):
            inverse.append(-sum((polynomial[k]*inverse[j-k] for k in range(1,j+1)),Fraction(0)))
            budget.tick(j)
        x=Fraction(-node.t,alpha)
        answer.append((node.t,tuple(at_zero*sum((inverse[k]*x**(j+k) for k in range(order-j)),Fraction(0))
                                    for j in range(min(order,degree+1)))))
    return tuple(answer)

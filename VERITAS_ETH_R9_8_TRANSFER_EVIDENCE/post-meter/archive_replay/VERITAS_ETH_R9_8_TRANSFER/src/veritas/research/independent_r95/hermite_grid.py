"""Finite exact checks of eq:tensor-hermite-loss; no production interpolation."""
from fractions import Fraction


def valuation(x):
    if type(x) is not int or x==0:raise ValueError('nonzero integer required')
    x=abs(x);v=0
    while x%2==0:x//=2;v+=1
    return v


def check_grid(*,a,u,M,p):
    if any(type(x) is not int for x in (a,u,M,p)) or not 1<=u<=a<=6 or not u<=M<=64 or not 1<=p<=1024:
        raise ValueError('bounded Hermite grid parameters required')
    L=2**a;alpha=2*L;h=(3*M+u-1)//u
    multiplicity=lambda i:h*max(0,u-i)
    nodes={t:multiplicity(valuation(t)) for t in range(-L,L) if t}
    if sum(nodes.values())<=M*(2*L-1) or any(q>4*M for q in nodes.values()):
        raise ValueError('insufficient Hermite multiplicities')
    rows=[]
    for t,qt in nodes.items():
        if qt==0:continue
        i=valuation(t);D=L//2**i
        direct=sum(q*(valuation(s)-valuation(t-s)) for s,q in nodes.items() if s!=t)
        by_levels=sum((Fraction(D*j,2**j)*(multiplicity(i+j)-multiplicity(i)) for j in range(1,a-i+1)),Fraction(0))
        if direct!=by_levels or direct < -6*D*h:raise ValueError('tapered grid valuation identity failed')
        if any(valuation(alpha)<valuation(t-s) for s,q in nodes.items() if s!=t and q):
            raise ValueError('reciprocal Taylor factor not integral')
        pt=p+8*h*D+8*M*(a+1)
        # Each quotient coefficient is integral; the largest evaluation loss
        # occurs at j=q_t-1. Check the exact loss, not just the guard formula.
        minimum=direct+(qt-1)*(i-a-1)
        if pt+minimum<p:raise ValueError('guard insufficient for a quotient coefficient')
        rows.append({'t':t,'multiplicity':qt,'precision':pt,'E_at_zero_valuation':direct,
                     'minimum_multiplier_valuation':minimum,'guard_margin':pt+minimum-p})
    return {'a':a,'u':u,'M':M,'p':p,'points_checked':len(rows),'rows':rows,
            'status':'FINITE_GRID_IDENTITY_CHECKED','universal_proof':False}

"""Exact local Cauchy polynomial identity from the manuscript.

For S=[-L, ..., L-1], C(T)=prod(T-t),
W_xy(T)=C(T) / (C'(0)*(T-(y-x))).  Removable singularities are
handled algebraically by polynomial division, not by float limits.
"""
from fractions import Fraction


def poly_mul(a, b):
    out = [0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            out[i+j] += x*y
    return tuple(out)


def _divide_linear_exact(coeffs, root):
    q=[0]*(len(coeffs)-1)
    q[-1]=coeffs[-1]
    for k in range(len(q)-2,-1,-1):
        q[k]=coeffs[k+1]+root*q[k+1]
    if coeffs[0]+root*q[0] != 0:
        raise ArithmeticError("not divisible by linear root")
    return tuple(q)


def cauchy_matrix_polynomials(L):
    if type(L) is not int or not 1 <= L <= 16:
        raise ValueError("bounded exact reference supports 1<=L<=16")
    S=range(-L,L)
    c=(1,)
    for t in S:
        c=poly_mul(c,(-t,1))
    # Because 0 belongs to S and its multiplicity is exactly one:
    derivative_at_zero=c[1]
    return tuple(tuple(tuple(Fraction(v,derivative_at_zero)
                              for v in _divide_linear_exact(c,y-x))
                       for y in range(L)) for x in range(L))


def evaluate(coeffs,t):
    z=Fraction(0)
    for x in reversed(coeffs):
        z=z*t+x
    return z


def verify_cauchy_matrix(L):
    matrix=cauchy_matrix_polynomials(L)
    for x in range(L):
        for y in range(L):
            if evaluate(matrix[x][y],0) != int(x==y):
                return False
    return True

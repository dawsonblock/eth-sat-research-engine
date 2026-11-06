"""Polynomial arithmetic over F2 with independent Rabin irreducibility test."""

def degree(a: int):
    return a.bit_length()-1


def mod(a: int, f: int):
    if f < 1:
        raise ValueError("invalid modulus polynomial")
    d=degree(f)
    while a and degree(a)>=d:
        a ^= f << (degree(a)-d)
    return a


def multiply_mod(a: int, b: int, f: int):
    z=0
    while b:
        if b & 1:
            z ^= a
        b >>= 1
        a <<= 1
    return mod(z,f)


def pow_mod(a: int, n: int, f: int):
    if n<0:
        raise ValueError('exponent must be nonnegative')
    z=1
    while n:
        if n&1:
            z=multiply_mod(z,a,f)
        a=multiply_mod(a,a,f)
        n >>= 1
    return z


def gcd(a: int,b: int):
    while b:
        a,b=b,mod(a,b)
    return a


def is_irreducible(f: int):
    d=degree(f)
    if d<1 or (f & 1)==0 or (f >> d) != 1:
        return False
    x=mod(2,f)
    y=x
    for k in range(1,d+1):
        y=multiply_mod(y,y,f)
        if d%k == 0 and k<d and (d//k)>1:
            # Stronger than necessary but valid: test all k dividing d.
            if gcd(y ^ x,f)!=1:
                return False
    return y==x


def first_irreducible(d: int):
    if not isinstance(d,int) or not 1<=d<=24:
        raise ValueError("degree 1..24 supported")
    for low in range(1,1<<d,2):
        f=(1<<d)|low
        if is_irreducible(f):
            return f
    raise ArithmeticError("no irreducible polynomial found")

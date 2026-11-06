"""Independent exact arithmetic audit; run with the review checkout on PYTHONPATH.

This script is review evidence, outside both sealed source releases. Its
confluent Vandermonde solver does not use either Hermite weight constructor.
"""
from fractions import Fraction as Q
from hashlib import sha256
from math import comb, isqrt, prod
from pathlib import Path
import json
import time

from veritas.research.eth_interpolation.source_hermite import make_source_tapered_plan


def v2(n):
    if not n:
        return 10**9
    n = abs(n)
    return (n & -n).bit_length() - 1


def val(x):
    x = Q(x)
    return v2(x.numerator) - v2(x.denominator) if x else 10**9


def mul(p, q):
    out = [Q(0)] * (len(p) + len(q) - 1)
    for i, x in enumerate(p):
        for j, y in enumerate(q):
            out[i+j] += x*y
    return out


def shifted_cauchy(L, t, difference):
    denominator = prod(-j for j in range(-L, L) if j)
    p = [Q(1, denominator)]
    for j in range(-L, L):
        if j != difference:
            p = mul(p, [Q(t-j), Q(2*L)])
    return p


def cauchy_integrality():
    cases = 0
    for a in range(1, 5):
        L = 1 << a
        for t in range(-L, L):
            for d in range(-L+1, L):
                p = shifted_cauchy(L, t, d)
                lower = 0 if d == t else a + 1 - v2(t-d)
                assert all(val(c) >= lower for c in p)
                if t == 0:
                    assert p[0] == int(d == 0)
                cases += 1
    return {"status": "PASS_FINITE_EXACT_COEFFICIENT_CHECK", "shifted_polynomials": cases,
            "a_range": [1, 4], "all_coefficients_integral": True,
            "off_diagonal_content_bound_checked": True}


def rational_W(L, T, d):
    return Q(prod(T-j for j in range(-L, L) if j != d),
             prod(-j for j in range(-L, L) if j))


def geometric_remainder():
    cases = 0
    for a in range(1, 4):
        L = 1 << a
        for t in range(-L, L):
            if not t or v2(t) >= a:
                continue
            i = v2(t)
            B = 1 << (i+1)
            for x in range(L):
                for y in range(L):
                    if ((x >> i) & 1) != ((y >> i) & 1):
                        continue
                    y0, j = y % B, y // B
                    for zeta in (0, 1, 2):
                        T = t + 2*L*zeta
                        denominator = T-y0+x
                        assert v2(denominator) <= i
                        base, ratio = rational_W(L, T, y0-x), Q(B, denominator)
                        actual = rational_W(L, T, y-x)
                        for precision in (1, 2, 5, 11):
                            expansion = sum((base*ratio**b*j**b
                                             for b in range(precision-1)), Q(0))
                            assert val(actual-expansion) >= precision
                            assert all(val(base*ratio**b) >= b+1
                                       for b in range(precision-1))
                            cases += 1
    return {"status": "PASS_FINITE_EXACT_RATIONAL_REMAINDER", "cases": cases,
            "a_range": [1, 3], "precision_cases": [1, 2, 5, 11]}


def solve(A, b):
    """Exact Gauss-Jordan solve, separate from the product-form Hermite code."""
    matrix = [[Q(x) for x in row] + [Q(y)] for row, y in zip(A, b)]
    n = len(b)
    for col in range(n):
        pivot = next(i for i in range(col, n) if matrix[i][col])
        matrix[pivot], matrix[col] = matrix[col], matrix[pivot]
        scale = matrix[col][col]
        matrix[col][col:] = [x/scale for x in matrix[col][col:]]
        for i in range(n):
            if i != col and matrix[i][col]:
                scale = matrix[i][col]
                matrix[i][col:] = [x-scale*y for x, y in zip(matrix[i][col:], matrix[col][col:])]
    return [row[-1] for row in matrix]


def mod_odd(x, precision):
    assert x.denominator % 2
    modulus = 1 << precision
    return x.numerator * pow(x.denominator, -1, modulus) % modulus


def hermite_independent():
    records = []
    for M, a, u in ((1,1,1), (2,1,1), (1,2,1), (2,2,2), (1,3,1), (2,3,2)):
        L, p = 1 << a, 7
        h = (3*M+u-1)//u
        nodes = [(t, h*(u-v2(t))) for t in range(-L, L) if t and v2(t) < u]
        coordinates = [(t, j) for t, q in nodes for j in range(q)]
        n = len(coordinates)
        A = [[comb(k,j)*t**(k-j)*(2*L)**j if j <= k else 0
              for t,j in coordinates] for k in range(n)]
        weights = solve(A, [1] + [0]*(n-1))
        assert all(sum(w*x for w,x in zip(weights,row)) == int(k == 0)
                   for k,row in enumerate(A))
        plan = make_source_tapered_plan(M=M, a=a, u=u, p=p, max_terms=256)
        production = {(t,j): w for t,row in plan.weights for j,w in enumerate(row)}
        assert all(production[t,j] == w for (t,j),w in zip(coordinates,weights)
                   if (t,j) in production)
        minimum_margin = min(p + 8*h*(L >> v2(t)) + 8*M*(a+1) + val(w) - p
                             for (t,j),w in zip(coordinates,weights) if w)
        assert minimum_margin >= 0
        # A degree-bounded rational polynomial satisfying shifted integrality:
        # F(T) = W_00(T)^M + 3 W_01(T)^M - 5, with F(0)=-4.
        jets = {}
        for t, q in nodes:
            w0, w1 = [Q(1)], [Q(1)]
            for _ in range(M):
                w0 = mul(w0, shifted_cauchy(L,t,0))
                w1 = mul(w1, shifted_cauchy(L,t,1))
            poly = [x+3*y for x,y in zip(w0,w1)]
            poly[0] -= 5
            bits = p + 8*h*(L >> v2(t)) + 8*M*(a+1)
            jets[t] = [mod_odd(poly[j] if j < len(poly) else Q(0), bits) for j in range(q)]
        recovered = sum((w*jets[t][j] for (t,j),w in zip(coordinates,weights)), Q(0))
        assert mod_odd(recovered,p) == (-4) % (1 << p)
        records.append({"M": M, "a": a, "u": u, "matrix_order": n,
                        "independent_weights_agree": True,
                        "minimum_coefficient_error_margin_bits": minimum_margin,
                        "rational_polynomial_recovered": 124})
    return {"status": "PASS_INDEPENDENT_CONFLUENT_VANDERMONDE", "cases": records,
            "universal_proof": False}


def root_is_not_path_admission():
    lam = 131080
    s = 1 << lam
    delta = 1 << (9*lam//10)
    H = (s+isqrt(lam)-1)//isqrt(lam)
    records = []
    for depth, M in ((0,s), (1,s//32)):
        us = [lam // (131072*(1 << d)) for d in range(depth+1)]
        a = 2*sum(us)
        L, D = 1 << a, 1 << (12*a)
        checks = [M >= 2*D*D*delta, M >= L*D, 2*L <= delta]
        assert all(checks) and M > H
        records.append({"depth": depth, "M_log2": lam-5*depth,
                        "a": a, "u": us[-1], "above_leaf_cutoff": True,
                        "three_packing_inequalities": checks})
    assert records[0]["u"] == 1 and records[1]["u"] == 0
    return {"status": "EXACT_NUMERIC_COUNTEREXAMPLE_TO_ROOT_ONLY_ADMISSION",
            "root_s": "2^131080", "leaf_divisor": isqrt(lam), "path": records,
            "network_constructed": False,
            "not_a_counterexample_to_sufficiently_large_manuscript_theorem": True}


if __name__ == "__main__":
    start = time.monotonic()
    results = {"status": "PASS_BOUNDED_MATH_REVIEW", "source_qualified": False,
               "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
               "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
               "cauchy": cauchy_integrality(), "geometric_modes": geometric_remainder(),
               "hermite": hermite_independent(), "source_path": root_is_not_path_admission()}
    results["seconds"] = time.monotonic()-start
    results["script_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    Path(__file__).with_name("math_checks.json").write_text(json.dumps(results, indent=2)+"\n")
    print(json.dumps(results))

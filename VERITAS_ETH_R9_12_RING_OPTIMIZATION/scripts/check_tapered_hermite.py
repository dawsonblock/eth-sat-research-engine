"""Exact check of lem:tapered-hermite on the paper's deformed contraction F(T).

Run with no arguments for the recovery cases, or with `neg` for the negative control
(precision one bit below the actual loss, which must fail on some seeds).
"""
import itertools
import random
import sys
from fractions import Fraction as Fr


def v2(x):
    x = Fr(x)
    if x == 0:
        return 10**9
    n, d = x.numerator, x.denominator
    v = 0
    while n % 2 == 0:
        n //= 2; v += 1
    while d % 2 == 0:
        d //= 2; v -= 1
    return v


def pmul(a, b):
    r = [Fr(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                r[i + j] += x * y
    return r


def padd(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)]


def pscale(a, c):
    return [x * c for x in a]


def peval(a, x):
    r = Fr(0)
    for c in reversed(a):
        r = r * x + c
    return r


def compose_linear(a, t, al):
    """a(t + al*z) as polynomial in z."""
    r = [Fr(0)]
    for c in reversed(a):
        r = padd(pmul(r, [Fr(t), Fr(al)]), [c])
    return r


def series_inv(a, n):
    inv = [Fr(0)] * n
    inv[0] = 1 / a[0]
    for k in range(1, n):
        s = sum(a[j] * inv[k - j] for j in range(1, min(k, len(a) - 1) + 1))
        inv[k] = -s / a[0]
    return inv


def run(a, u, M, p, seed, short=0):
    rng = random.Random(seed)
    L = 2 ** a
    al = 2 ** (a + 1)
    S = list(range(-L, L))
    C = [Fr(1)]
    for s in S:
        C = pmul(C, [Fr(-s), Fr(1)])
    Cp0 = Fr(1)
    for s in S:
        if s != 0:
            Cp0 *= -s
    slots = sorted(rng.sample(range(L), M))

    def W(x, y):
        d = y - x
        q = [Fr(1)]
        for s in S:
            if s != d:
                q = pmul(q, [Fr(-s), Fr(1)])
        return pscale(q, 1 / Cp0)

    Wm = [[W(x, y) for y in slots] for x in slots]
    A = {Y: rng.randint(-50, 50) for Y in itertools.product((0, 1), repeat=M)}
    B = {X: rng.randint(-50, 50) for X in itertools.product((0, 1), repeat=M)}
    F = [Fr(0)]
    for X in B:
        rowf = []
        for r in range(M):
            f = [Fr(0)]
            for c in range(M):
                if X[c]:
                    f = padd(f, Wm[r][c])
            rowf.append(f)
        for Y in A:
            coef = A[Y] * B[X]
            if coef == 0:
                continue
            prod = [Fr(coef)]
            for r in range(M):
                lf = rowf[r] if Y[r] else padd([Fr(1)], pscale(rowf[r], -1))
                prod = pmul(prod, lf)
            F = padd(F, prod)
    F0 = F[0]
    assert F0 == sum(A[X] * B[X] for X in A), "F(0) is not the contraction"
    assert len(F) - 1 <= M * (2 * L - 1)
    for t in S:
        G = compose_linear(F, t, al)
        assert all(v2(c) >= 0 for c in G), f"F(t+az) not integral at t={t}"

    h = -(-3 * M // u)
    q = {t: h * max(0, u - v2(t)) for t in S if t != 0}
    nodes = [t for t in q if q[t] > 0]
    assert sum(q.values()) > len(F) - 1
    total = Fr(0)
    worst_loss = 10**9
    for t in nodes:
        i = v2(t); D = L // 2 ** i
        Et0_pre = Fr(1)
        for s_ in nodes:
            if s_ != t:
                Et0_pre *= Fr(-s_, t - s_) ** q[s_]
        true_loss = -min(v2(Et0_pre * Fr(-t, al) ** j) for j in range(q[t]))
        pt = p + 8 * h * D + 8 * M * (a + 1) if not short else p + true_loss - 1
        bound = 6 * D * h + 4 * M * (a + 1)
        G = compose_linear(F, t, al)[: q[t]]
        G += [Fr(0)] * (q[t] - len(G))
        G = [c + rng.randint(-3, 3) * 2 ** pt for c in G]
        Et = [Fr(1)]
        Et0 = Fr(1)
        for s in nodes:
            if s in (t,):
                continue
            fac = [Fr(1), Fr(al, t - s)]
            for _ in range(q[s]):
                Et = pmul(Et, fac)[: q[t]]
            Et0 *= Fr(-s, t - s) ** q[s]
        assert all(v2(c) >= 0 for c in Et) and Et[0] == 1
        inv = series_inv(Et, q[t])
        assert all(v2(c) >= 0 for c in inv)
        Q = pmul(G, inv)[: q[t]]
        w = Fr(-t, al)
        loss = -min(v2(Et0 * w ** j) for j in range(q[t]))
        worst_loss = min(worst_loss, bound - loss)
        assert loss <= bound, (t, loss, bound)
        total += Et0 * peval(Q, w)
    ok = v2(total - F0) >= p
    return ok, worst_loss, len(nodes)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fails = 0
        for (a, u, M) in [(2, 2, 2), (3, 2, 3), (3, 3, 3)]:
            for seed in range(5):
                ok, _, _ = run(a, u, M, p=5, seed=seed, short=1)
                fails += not ok
        print("negative control failures:", fails, "of 15")
        sys.exit(0)
    cases = [(2, 1, 1), (2, 2, 2), (2, 2, 3), (3, 1, 2), (3, 2, 3), (3, 3, 3), (3, 2, 4), (3, 3, 5)]
    allok = True
    for (a, u, M) in cases:
        for seed in range(3):
            ok, slack, n = run(a, u, M, p=5, seed=seed)
            print(f"a={a} u={u} M={M} seed={seed} nodes={n} recovered_mod_2^5={ok} min(bound-loss)={slack}")
            allok &= ok
    print("ALL_OK" if allok else "FAIL")
    sys.exit(0 if allok else 1)

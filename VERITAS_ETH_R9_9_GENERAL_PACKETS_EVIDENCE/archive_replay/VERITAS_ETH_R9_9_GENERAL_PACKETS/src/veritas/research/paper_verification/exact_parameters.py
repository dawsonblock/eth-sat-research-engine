"""Bounded evaluators of the pinned integer formulas, separate from the executor."""

from math import isqrt
from veritas.research.appendix_d_schedule import schedule_preflight


def _int(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("unsupported " + name)


def source_schedule(s, depth):
    if type(s) is not int or s < 2 or s.bit_length() > 262201:
        raise ValueError("unsupported s or zero leaf denominator")
    _int(depth, 0, 4096, "depth")
    lam = (s - 1).bit_length()
    target = s**9
    if s.bit_length() <= 4096:
        lo, hi = 0, 1 << ((target.bit_length() + 9) // 10)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if mid**10 >= target:
                hi = mid
            else:
                lo = mid
        delta = hi
    elif s == 1 << lam and lam % 10 == 0:
        delta = 1 << (9 * lam // 10)
    else:
        raise ValueError(
            "large-size reference supports powers of 2 with exponent divisible by 10"
        )
    if not (delta - 1) ** 10 < target <= delta**10:
        raise ArithmeticError("invalid degree threshold")
    us = [lam // (131072 * (1 << d)) for d in range(depth + 1)]
    a = 2 * sum(us)
    return {
        "lambda": lam,
        "leaf_threshold": -(-s // isqrt(lam)),
        "degree_limit": delta,
        "extension_degree": 4 * lam,
        "u": us[-1],
        "a": a,
        "a_previous": a - 2 * us[-1],
        "r": 64,
        "L": 1 << a,
        "packing_class_count": 64 ** (2 * a),
    }


def check_schedule(s, M, degree, depth, *, size_constant=1):
    q = source_schedule(s, depth)
    if (
        any(type(v) is not int or v < 0 for v in (M, degree))
        or type(size_constant) is not int
        or size_constant < 1
    ):
        raise ValueError("invalid network statistics")
    D, L, delta = q["packing_class_count"], q["L"], q["degree_limit"]
    checks = {
        "M_ge_2_D_squared_delta": M >= 2 * D * D * delta,
        "M_ge_LD": M >= L * D,
        "2L_le_delta": 2 * L <= delta,
    }
    if degree > M:
        expected = "INVALID_DEGREE"
    elif M * (8**depth) > size_constant * s:
        expected = "INVALID_RECURSIVE_SIZE_BOUND"
    elif degree > delta:
        expected = "INVALID_DEGREE_BOUND"
    elif M <= q["leaf_threshold"]:
        expected = "DIRECT_LEAF_ALLOWED"
    elif not q["u"]:
        expected = "INCONCLUSIVE_SCHEDULE"
    elif all(checks.values()):
        expected = "ACTIVE_NUMERIC_PRECONDITIONS_MET"
    else:
        expected = "INCONCLUSIVE_PACKING"
    actual = schedule_preflight(
        s, M, degree, depth, size_constant=size_constant, max_size_bits=262201
    )
    if actual["status"] != expected or any(actual[k] != q[k] for k in q if k in actual):
        raise ValueError("executor schedule disagrees with exact reference")
    if "numeric_preconditions" in actual and (
        actual["numeric_preconditions"] != checks
        or actual["label_class_exponent"] != D.bit_length() - 1
        or actual["packet_size_exponent"] != q["a"]
    ):
        raise ValueError("executor packing conditions differ")
    return {
        "status": expected,
        "parameters": q,
        "packing_conditions": checks,
        "active_identity_proved": False,
    }


def hermite_parameters(M, a, u, p, *, max_wires=32, max_precision=1024):
    _int(max_wires, 1, 1024, "maximum wires")
    _int(max_precision, 1, 65536, "maximum precision")
    _int(M, 1, max_wires, "M")
    _int(a, 1, 3, "a")
    _int(u, 1, min(M, a), "u")
    _int(p, 1, max_precision, "precision")
    L = 1 << a
    h = -(-3 * M // u)
    nodes = []
    for t in range(-L, L):
        if t == 0:
            continue
        i = 0
        while t % (2 ** (i + 1)) == 0:
            i += 1
        if i < u:
            scale = L // (2**i)
            nodes.append(
                (t, i, h * (u - i), scale, p + 8 * h * scale + 8 * M * (a + 1))
            )
    return {"alpha": 2 * L, "degree_bound": M * (2 * L - 1), "h": h, "nodes": nodes}

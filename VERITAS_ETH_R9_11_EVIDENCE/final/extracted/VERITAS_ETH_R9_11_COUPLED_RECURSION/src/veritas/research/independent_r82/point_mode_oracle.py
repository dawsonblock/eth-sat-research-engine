"""Independent finite Cauchy and mode-action verifier.

This module intentionally does not import the production point-mode builder,
checker, packing helpers, matching routines, or production ring. It computes
the paper's polynomial C(T)=prod_q(T-q), divides C(T) by T-(y-x) over Q,
normalizes by C'(0), shifts exactly, and evaluates in a separately coded
bounded unramified 2-adic quotient. It then checks both the independent
geometric-mode construction and any supplied local-plus-mode decomposition
entrywise against that direct polynomial.

The packet labels and occupied-slot records are inputs to this checker; their
global packing theorem is outside this finite certificate. The shared
mathematical premise is the source's declared packet/label interpretation and
the pinned paper's Cauchy/mode equations (eq:tensor-cauchy and
eq:tensor-mode-expansion in subsec:tensor-modes).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from fractions import Fraction
from itertools import product
from math import comb, isfinite
from time import monotonic


class OracleBudgetExceeded(RuntimeError):
    status = "INCONCLUSIVE_RESOURCE_LIMIT"

    def __init__(self, message, *, resource_failure=None):
        super().__init__(message)
        self.resource_failure = resource_failure


@dataclass(frozen=True)
class OracleLimits:
    """Explicit finite per-invocation limits; never an arithmetic qualification."""
    max_work: int = 5_000_000
    max_seconds: int = 60

    def __post_init__(self):
        if type(self.max_work) is not int or not 1 <= self.max_work <= 1_000_000_000:
            raise ValueError('oracle work limit must be 1..1000000000')
        if type(self.max_seconds) is not int or not 1 <= self.max_seconds <= 3600:
            raise ValueError('oracle time limit must be 1..3600 seconds')

    def record(self):
        return asdict(self)


def meter_from_budget(budget, scope):
    """Respect explicit oracle policy and remaining overall wall-time/work.

    A meter's wall clock includes nested computation between its operations.
    Older callers without an explicit policy retain their 5M/60s defaults.
    """
    budget.tick(0)
    limits = getattr(budget, 'oracle_limits', OracleLimits())
    if type(limits) is not OracleLimits:
        raise TypeError('validated OracleLimits required')
    remaining_work = budget.policy.max_work-budget.work
    remaining_time = budget.policy.max_seconds-(monotonic()-budget.started)
    if remaining_work <= 0 or remaining_time <= 0:
        resource = 'WORK_UNITS' if remaining_work <= 0 else 'WALL_TIME_US'
        raise OracleBudgetExceeded('overall budget exhausted before independent oracle',
            resource_failure={'scope':scope, 'resource':resource, 'limit_scope':'GLOBAL',
                              'remaining_work_units':max(0,remaining_work),
                              'remaining_time_us':max(0,int(remaining_time*1_000_000))})
    return _Meter(min(limits.max_work,remaining_work), min(limits.max_seconds,remaining_time),
                  limits=limits, scope=scope, global_budget=budget,
                  work_limit_scope='ORACLE' if limits.max_work <= remaining_work else 'GLOBAL_REMAINDER',
                  time_limit_scope='ORACLE' if limits.max_seconds < remaining_time else 'GLOBAL_REMAINDER')


class UnsupportedIntegralShift(ValueError):
    pass


@dataclass
class _Meter:
    maximum: int
    timeout_s: float
    used: int = 0
    started: float = 0.0
    limits: OracleLimits | None = None
    scope: str = 'independent Cauchy/mode oracle'
    work_limit_scope: str = 'ORACLE'
    time_limit_scope: str = 'ORACLE'
    global_budget: object | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.limits is not None and type(self.limits) is not OracleLimits:
            raise TypeError('validated OracleLimits required')
        work_cap = self.limits.max_work if self.limits is not None else 5_000_000
        seconds_cap = self.limits.max_seconds if self.limits is not None else 120
        if type(self.maximum) is not int or not 1 <= self.maximum <= work_cap:
            raise ValueError("independent oracle work cap exceeds validated policy")
        if (type(self.timeout_s) not in (int, float) or not isfinite(self.timeout_s)
                or not 0 < self.timeout_s <= seconds_cap):
            raise ValueError("independent oracle timeout exceeds validated policy")
        self.started = monotonic()

    def tick(self, amount=1):
        if type(amount) is not int or amount < 0:
            raise ValueError('nonnegative oracle work charge required')
        self.used += amount
        elapsed = monotonic()-self.started
        if self.used > self.maximum or elapsed > self.timeout_s:
            work = self.used > self.maximum
            failure = {'scope':self.scope, 'resource':'WORK_UNITS' if work else 'WALL_TIME_US',
                'limit':self.maximum if work else int(self.timeout_s*1_000_000),
                'observed':self.used if work else int(elapsed*1_000_000),
                'used_work_units':self.used, 'elapsed_us':int(elapsed*1_000_000),
                'limit_scope':self.work_limit_scope if work else self.time_limit_scope,
                'clock_scope':'METER_LIFETIME_INCLUDING_NESTED_COMPUTATION'}
            if failure['limit_scope'] == 'GLOBAL_REMAINDER' and self.global_budget is not None:
                # Preserve the enclosing budget's exception contract. Charge the
                # pending work exactly once on this abort path; no result returns
                # to the caller that would normally charge the completed meter.
                try:
                    self.global_budget.tick(self.used)
                except ValueError as exc:
                    if getattr(exc, 'status', None) == 'INCONCLUSIVE_RESOURCE_LIMIT':
                        exc.resource_failure = failure
                    raise
            raise OracleBudgetExceeded('independent oracle '+('work' if work else 'time')+' limit exceeded',
                                       resource_failure=failure)


def _degree(poly: int) -> int:
    return poly.bit_length() - 1


def _poly_mod(a: int, f: int) -> int:
    d = _degree(f)
    while a and _degree(a) >= d:
        a ^= f << (_degree(a) - d)
    return a


def _poly_mul_mod(a: int, b: int, f: int) -> int:
    out = 0
    while b:
        if b & 1:
            out ^= a
        b >>= 1
        a <<= 1
    return _poly_mod(out, f)


def _poly_pow_mod(a: int, n: int, f: int) -> int:
    out = 1
    while n:
        if n & 1:
            out = _poly_mul_mod(out, a, f)
        a = _poly_mul_mod(a, a, f)
        n >>= 1
    return out


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_mod(a, b)
    return a


def _prime_factors(n: int) -> tuple[int, ...]:
    result = []
    q = 2
    while q * q <= n:
        if n % q == 0:
            result.append(q)
            while n % q == 0:
                n //= q
        q += 1
    if n > 1:
        result.append(n)
    return tuple(result)


def _irreducible(f: int, *, max_extension_degree: int = 8) -> bool:
    if (type(max_extension_degree) is not int or not 2 <= max_extension_degree <= 16):
        raise ValueError("independent extension degree cap must be in 2..16")
    if type(f) is not int or not 2 <= _degree(f) <= max_extension_degree or not f & 1:
        return False
    e = _degree(f)
    x = 2
    for q in _prime_factors(e):
        if _poly_gcd(_poly_pow_mod(x, 1 << (e // q), f) ^ x, f) != 1:
            return False
    return _poly_pow_mod(x, 1 << e, f) == x


class _IndependentExtension:
    """Small Z/2^p[U]/(f) arithmetic with its own irreducibility and inverse checks."""

    def __init__(self, precision: int, f: int, meter: _Meter, *, max_precision_bits=1024,
                 max_extension_degree=8):
        if type(max_precision_bits) is not int or not 1 <= max_precision_bits <= 65536:
            raise ValueError("unsupported independent precision cap")
        if type(precision) is not int or not 1 <= precision <= max_precision_bits:
            raise ValueError(f"precision must be in 1..{max_precision_bits}")
        if not _irreducible(f, max_extension_degree=max_extension_degree):
            raise ValueError(
                f"extension polynomial is not irreducible of degree 2..{max_extension_degree}"
            )
        self.p = precision
        self.f = f
        self.e = _degree(f)
        self.modulus = 1 << precision
        self.meter = meter

    def elem(self, values):
        values = tuple(values)
        if len(values) > self.e or any(type(v) is not int for v in values):
            raise ValueError("invalid extension coordinates")
        return tuple(v % self.modulus for v in values) + (0,) * (self.e - len(values))

    @property
    def zero(self):
        return (0,) * self.e

    @property
    def one(self):
        return (1,) + (0,) * (self.e - 1)

    def add(self, a, b):
        self.meter.tick(self.e)
        return tuple((x + y) % self.modulus for x, y in zip(a, b))

    def neg(self, a):
        self.meter.tick(self.e)
        return tuple((-x) % self.modulus for x in a)

    def sub(self, a, b):
        return self.add(a, self.neg(b))

    def mul(self, a, b):
        e = self.e
        self.meter.tick(e * e)
        terms = [0] * (2 * e - 1)
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                terms[i + j] = (terms[i + j] + x * y) % self.modulus
        for k in range(2 * e - 2, e - 1, -1):
            value = terms[k]
            if value:
                for i in range(e):
                    if (self.f >> i) & 1:
                        terms[k - e + i] = (terms[k - e + i] - value) % self.modulus
        return tuple(terms[:e])

    def scalar(self, value: Fraction | int):
        value = Fraction(value)
        den = value.denominator
        if den % 2 == 0:
            raise UnsupportedIntegralShift("shifted Cauchy coefficient has an even denominator")
        self.meter.tick(max(1, den.bit_length() // 64 + value.numerator.bit_length() // 64))
        residue = (value.numerator * pow(den, -1, self.modulus)) % self.modulus
        return self.elem((residue,))

    def is_unit(self, a):
        return any(v & 1 for v in a)

    def valuation(self, a):
        if not any(a):
            return self.p
        return min((v & -v).bit_length() - 1 if v else self.p for v in a)

    def inverse(self, a):
        if not self.is_unit(a):
            raise ZeroDivisionError("attempted inverse of a nonunit")
        parity = sum((v & 1) << i for i, v in enumerate(a))
        inverse_bits = None
        for candidate in range(1, 1 << self.e):
            self.meter.tick()
            if _poly_mul_mod(parity, candidate, self.f) == 1:
                inverse_bits = candidate
                break
        if inverse_bits is None:
            raise ArithmeticError("unit has no residue-field inverse")
        y = self.elem(tuple((inverse_bits >> i) & 1 for i in range(self.e)))
        two = self.elem((2,))
        accuracy = 1
        while accuracy < self.p:
            y = self.mul(y, self.sub(two, self.mul(a, y)))
            accuracy *= 2
        if self.mul(a, y) != self.one:
            raise ArithmeticError("independent Hensel inverse verification failed")
        return y

    def pow(self, a, exponent: int):
        if type(exponent) is not int or exponent < 0:
            raise ValueError("nonnegative integer exponent required")
        out = self.one
        while exponent:
            self.meter.tick()
            if exponent & 1:
                out = self.mul(out, a)
            a = self.mul(a, a)
            exponent >>= 1
        return out


def cauchy_polynomial(L: int, x: int, y: int, *, meter: _Meter | None = None):
    """Return exact Fraction coefficients of [C(T)/(T-(y-x))]/C'(0)."""
    if type(L) is not int or not 1 <= L <= 8 or L & (L - 1):
        raise ValueError("L must be a power of two in 1..8")
    if type(x) is not int or type(y) is not int or not (0 <= x < L and 0 <= y < L):
        raise ValueError("Cauchy indices are outside the packet")
    if meter is not None:
        meter.tick(2 * L)
    roots = tuple(range(-L, L))
    coeffs = [1]
    for root in roots:
        if meter is not None:
            meter.tick(len(coeffs))
        out = [0] * (len(coeffs) + 1)
        for i, coeff in enumerate(coeffs):
            out[i] -= root * coeff
            out[i + 1] += coeff
        coeffs = out
    q = y - x
    quotient = [0] * (len(coeffs) - 1)
    remainder = list(coeffs)
    for degree in range(len(remainder) - 1, 0, -1):
        if meter is not None:
            meter.tick()
        leading = remainder[degree]
        quotient[degree - 1] = leading
        remainder[degree] = 0
        remainder[degree - 1] += q * leading
    if remainder[0] != 0:
        raise ArithmeticError("exact division by T-(y-x) left a remainder")
    derivative = 1
    for root in roots:
        if root:
            derivative *= -root
    if derivative == 0:
        raise ArithmeticError("C'(0) unexpectedly vanished")
    polynomial = tuple(Fraction(coef, derivative) for coef in quotient)
    value_at_zero = polynomial[0]
    if value_at_zero != (1 if q == 0 else 0):
        raise ArithmeticError("W(0)=I check failed")
    return polynomial


def shifted_cauchy_polynomial(L: int, node: int, alpha: int, x: int, y: int,
                              *, meter: _Meter | None = None):
    """Exact coefficients of W_xy(node+alpha Z), formed over Q first."""
    if type(node) is not int or type(alpha) is not int or alpha <= 0:
        raise ValueError("integer node and positive scale required")
    original = cauchy_polynomial(L, x, y, meter=meter)
    shifted = [Fraction(0) for _ in original]
    for degree, coefficient in enumerate(original):
        for j in range(degree + 1):
            if meter is not None:
                meter.tick()
            shifted[j] += (coefficient * comb(degree, j) *
                           pow(node, degree - j) * pow(alpha, j))
    return tuple(shifted)


def _evaluate_shifted(ring: _IndependentExtension, coefficients, point):
    z = ring.zero
    for coefficient in reversed(coefficients):
        z = ring.add(ring.mul(z, point), ring.scalar(coefficient))
    return z


def _v2(value: int) -> int:
    if type(value) is not int or value == 0:
        raise ValueError("2-adic valuation requires a nonzero integer")
    value = abs(value)
    return (value & -value).bit_length() - 1


def _packet_slots(packet, L, edge_count):
    if not isinstance(packet, dict):
        raise ValueError("packet record must be a mapping")
    if "occupied_slots" in packet:
        entries = packet["occupied_slots"]
        if not isinstance(entries, (tuple, list)):
            raise ValueError("occupied_slots must be a sequence")
        pairs = []
        previous = -1
        for slot, edge_id in entries:
            if (type(slot) is not int or type(edge_id) is not int or
                    not 0 <= slot < L or not 0 <= edge_id < edge_count or slot <= previous):
                raise ValueError("invalid, repeated, or unordered occupied slot")
            previous = slot
            pairs.append((slot, edge_id))
        return tuple(pairs)
    slots = packet.get("slots")
    if not isinstance(slots, (tuple, list)) or len(slots) != L:
        raise ValueError("dense packet slots have incorrect length")
    result = []
    for slot, edge_id in enumerate(slots):
        if edge_id is not None:
            if type(edge_id) is not int or not 0 <= edge_id < edge_count:
                raise ValueError("invalid dense packet edge identifier")
            result.append((slot, edge_id))
    return tuple(result)


def _independent_network_edges(network):
    count = getattr(network, "edges", None)
    vertices = getattr(network, "vertices", None)
    if type(count) is not int or not isinstance(vertices, tuple):
        raise ValueError("immutable parent network required")
    owners = [{"row": None, "column": None} for _ in range(count)]
    indices = {"row": 0, "column": 0}
    for vertex in vertices:
        side = getattr(vertex, "side", None)
        ports = getattr(vertex, "ports", None)
        if side not in indices or not isinstance(ports, tuple):
            raise ValueError("invalid parent vertex incidence")
        owner_id = indices[side]
        indices[side] += 1
        for edge in ports:
            if type(edge) is not int or not 0 <= edge < count or owners[edge][side] is not None:
                raise ValueError("parent port incidence is not one-to-one")
            owners[edge][side] = owner_id
    if any(item["row"] is None or item["column"] is None for item in owners):
        raise ValueError("parent edge has a missing endpoint")
    return tuple((item["row"], item["column"]) for item in owners)


def _read_coord(ring, encoded):
    if not isinstance(encoded, (tuple, list)) or len(encoded) != ring.e:
        raise ValueError("mode coefficient has incorrect extension width")
    if any(type(v) is not int or not 0 <= v < ring.modulus for v in encoded):
        raise ValueError("mode coefficient is not a canonical residue")
    return tuple(encoded)


def verify_point_mode_action(source, certificate, *, max_entries=4096,
                             max_work=1_000_000, timeout_s=30.0):
    """Check finite mode action against an independent rational-polynomial oracle.

    The supplied mode basis is not required to equal the canonical basis
    produced by the paper's geometric formula. Correctness is the equality of
    the represented packet matrix with the exact independently constructed
    Cauchy matrix. The oracle separately constructs the canonical geometric
    expansion as an internal cross-check.
    """
    meter = None
    try:
        if type(max_entries) is not int or not 1 <= max_entries <= 100_000:
            raise ValueError("entry cap must be in 1..100000")
        meter = _Meter(max_work, timeout_s)
        if not isinstance(source, dict) or not isinstance(certificate, dict):
            raise ValueError("source and point certificate mappings required")
        L = source.get("L")
        node = certificate.get("node")
        precision = certificate.get("precision")
        f = certificate.get("irreducible_polynomial")
        if type(node) is not int or node == 0 or type(precision) is not int:
            raise ValueError("invalid interpolation node or precision")
        ring = _IndependentExtension(precision, f, meter)
        if certificate.get("extension_degree") != ring.e:
            raise ValueError("extension degree does not match its polynomial")
        zeta = _read_coord(ring, certificate.get("zeta"))
        if not (-L <= node < L and _v2(node) < L.bit_length() - 1):
            raise ValueError("node is outside the finite active Cauchy domain")
        alpha = 2 * L
        coordinate = _v2(node)
        B = 1 << (coordinate + 1)
        edges = source.get("edges")
        packets = source.get("packets")
        rows = source.get("row_labels")
        cols = source.get("column_labels")
        if not isinstance(edges, (tuple, list)) or not isinstance(packets, (tuple, list)):
            raise ValueError("source edge and packet arrays required")
        if not isinstance(rows, dict) or not isinstance(cols, dict):
            raise ValueError("source row and column labels required")
        edge_pairs = []
        for pair in edges:
            if (not isinstance(pair, (tuple, list)) or len(pair) != 2 or
                    any(type(v) is not int or v < 0 for v in pair)):
                raise ValueError("invalid source edge pair")
            edge_pairs.append(tuple(pair))
        packet_rows = []
        expected = {}
        total_entries = 0
        packet_layout = []
        for packet_id, packet in enumerate(packets):
            occupied = _packet_slots(packet, L, len(edge_pairs))
            row_entries, col_entries = [], []
            for slot, edge_id in occupied:
                u, v = edge_pairs[edge_id]
                row_label = rows.get(str(u))
                col_label = cols.get(str(v))
                if (not isinstance(row_label, (tuple, list)) or
                        not isinstance(col_label, (tuple, list)) or
                        len(row_label) != L.bit_length() - 1 or
                        len(col_label) != L.bit_length() - 1 or
                        any(type(q) is not int for q in (*row_label, *col_label))):
                    raise ValueError("invalid coordinate label on source edge")
                row_entries.append((slot, edge_id, row_label[coordinate]))
                col_entries.append((slot, edge_id, col_label[coordinate]))
            total_entries += len(row_entries) * len(col_entries)
            if total_entries > max_entries:
                raise OracleBudgetExceeded("independent packet-entry cap exceeded")
            packet_rows.append(row_entries)
            packet_layout.append((packet_id, row_entries, col_entries))
            for x, rid, _ in row_entries:
                for y, cid, _ in col_entries:
                    meter.tick()
                    key = (packet_id, rid, cid)
                    if key in expected:
                        raise ValueError("source repeats a row/column edge pair")
                    polynomial = shifted_cauchy_polynomial(L, node, alpha, x, y, meter=meter)
                    expected[key] = _evaluate_shifted(ring, polynomial, zeta)

        # Construct the paper's canonical local-plus-geometric action using
        # direct Cauchy coefficients and independently decoded packet labels.
        canonical = {key: ring.zero for key in expected}
        canonical_modes = 0
        canonical_terms = 0
        min_valuation_slack = precision
        for packet_id, row_entries, col_entries in packet_layout:
            by_y0 = {}
            target_groups = sorted({label for _, _, label in row_entries})
            for y, cid, source_group in col_entries:
                y0 = y % B
                j = (y - y0) // B
                by_y0.setdefault(y0, []).append((y, cid, source_group, j))
            for x, rid, target_group in row_entries:
                for y, cid, source_group in col_entries:
                    if source_group == target_group:
                        key = (packet_id, rid, cid)
                        poly = shifted_cauchy_polynomial(L, node, alpha, x, y, meter=meter)
                        canonical[key] = ring.add(canonical[key], _evaluate_shifted(ring, poly, zeta))
            for y0, tile_columns in sorted(by_y0.items()):
                source_groups = {item[2] for item in tile_columns}
                if len(source_groups) != 1:
                    raise ValueError("tile columns do not have one source group")
                source_group = next(iter(source_groups))
                for target_group in target_groups:
                    if target_group == source_group:
                        continue
                    target_rows = [(x, rid) for x, rid, group in row_entries if group == target_group]
                    if not target_rows:
                        continue
                    for exponent in range(precision - 1):
                        column_terms = [(cid, pow(j, exponent)) for _, cid, _, j in tile_columns
                                        if pow(j, exponent) != 0]
                        if not column_terms:
                            if exponent > 0:
                                break
                            continue
                        canonical_modes += 1
                        for x, rid in target_rows:
                            d = node - y0 + x
                            if d == 0 or _v2(d) > coordinate:
                                raise ValueError("cross-mode denominator violates its finite valuation premise")
                            v = _v2(d)
                            unit = ring.add(ring.scalar(d // (1 << v)),
                                            ring.mul(ring.scalar(alpha // (1 << v)), zeta))
                            if not ring.is_unit(unit):
                                raise ArithmeticError("normalized cross-mode denominator is not a unit")
                            base_poly = shifted_cauchy_polynomial(L, node, alpha, x, y0, meter=meter)
                            base = _evaluate_shifted(ring, base_poly, zeta)
                            ratio = ring.mul(ring.scalar(B // (1 << v)), ring.inverse(unit))
                            coefficient = ring.mul(base, ring.pow(ratio, exponent))
                            slack = ring.valuation(coefficient) - (exponent + 1)
                            min_valuation_slack = min(min_valuation_slack, slack)
                            if slack < 0:
                                raise ArithmeticError("independent mode violates its claimed 2-adic weight")
                            if coefficient == ring.zero:
                                continue
                            for cid, power in column_terms:
                                key = (packet_id, rid, cid)
                                canonical[key] = ring.add(canonical[key],
                                                          ring.mul(coefficient, ring.scalar(power)))
                                canonical_terms += 1
        if canonical != expected:
            raise ArithmeticError("independent geometric expansion differs from rational Cauchy matrix")

        # Evaluate the supplied representation, without canonical-name checks.
        represented = {key: ring.zero for key in expected}
        for item in certificate.get("local", ()):
            if not isinstance(item, (tuple, list)) or len(item) != 3:
                raise ValueError("malformed local Cauchy term")
            rid, cid, encoded = item
            if type(rid) is not int or type(cid) is not int:
                raise ValueError("local term identifiers must be integers")
            key_matches = [key for key in expected if key[1:] == (rid, cid)]
            if len(key_matches) != 1:
                raise ValueError("local term is absent or ambiguous in packet source")
            if not isinstance(encoded, (tuple, list)) or len(encoded) != 1:
                raise ValueError("local coefficient encoding must have one jet coordinate")
            value = _read_coord(ring, encoded[0])
            represented[key_matches[0]] = ring.add(represented[key_matches[0]], value)
        supplied_modes = certificate.get("modes", ())
        if not isinstance(supplied_modes, (tuple, list)):
            raise ValueError("mode list required")
        supplied_terms = 0
        mode_valuation_bounds = []
        for mode in supplied_modes:
            if not isinstance(mode, dict):
                raise ValueError("mode record must be a mapping")
            weight = mode.get("weight")
            if type(weight) is not int or weight < 1:
                raise ValueError("mode weight must be a positive integer")
            row_coefficients = {}
            actual_valuations = []
            for rid, encoded in mode.get("rows", ()):
                if type(rid) is not int or not isinstance(encoded, (tuple, list)) or len(encoded) != 1:
                    raise ValueError("malformed mode row coefficient")
                if rid in row_coefficients:
                    raise ValueError("duplicate row coefficient in a mode")
                coefficient = _read_coord(ring, encoded[0])
                if ring.valuation(coefficient) < weight:
                    raise ArithmeticError("declared mode weight exceeds independently checked valuation")
                actual_valuations.append(ring.valuation(coefficient))
                row_coefficients[rid] = coefficient
            mode_valuation_bounds.append({
                "minimum_actual_valuation": min(actual_valuations, default=precision),
                "claimed_weight": weight,
                "row_count": len(row_coefficients),
            })
            seen_columns = set()
            for cid, power in mode.get("column_terms", ()):
                if type(cid) is not int or type(power) is not int or power < 0:
                    raise ValueError("malformed mode column term")
                if cid in seen_columns:
                    raise ValueError("duplicate column term in a mode")
                seen_columns.add(cid)
                for key in expected:
                    if key[2] == cid and key[1] in row_coefficients:
                        term = ring.mul(row_coefficients[key[1]], ring.scalar(power))
                        represented[key] = ring.add(represented[key], term)
                        supplied_terms += 1
        if represented != expected:
            mismatches = sum(represented[key] != expected[key] for key in expected)
            raise ArithmeticError(f"supplied mode action differs from independent Cauchy matrix at {mismatches} entries")
        return {
            "valid": True,
            "status": "FINITE_INDEPENDENT_CAUCHY_MODE_ACTION_CHECKED",
            "claim": "FINITE_PACKET_ACTION_AT_ONE_SHIFTED_POINT",
            "packet_entry_count": len(expected),
            "production_mode_count": len(supplied_modes),
            "independent_canonical_mode_count": canonical_modes,
            "production_mode_term_count": supplied_terms,
            "independent_canonical_term_count": canonical_terms,
            "mode_valuation_bounds": mode_valuation_bounds,
            "minimum_weight_valuation_slack": min_valuation_slack,
            "precision_bits": precision,
            "node": node,
            "extension_degree": ring.e,
            "point": zeta,
            "work_units": meter.used,
            "hard_memory_limit_enforced": False,
            "universal_theorem_proven": False,
        }
    except OracleBudgetExceeded as exc:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT", "reason": str(exc),
                "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}
    except UnsupportedIntegralShift as exc:
        return {"valid": False, "status": "INCONCLUSIVE_UNSUPPORTED_INTEGRAL_SHIFT",
                "reason": str(exc), "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError,
            ZeroDivisionError) as exc:
        return {"valid": False, "status": "INVALID_INDEPENDENT_POINT_MODE_CERTIFICATE",
                "reason": str(exc), "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}


def independent_parent_point(network, source, certificate, *, max_edges=8,
                              max_work=2_000_000, timeout_s=30.0):
    """Exhaustively contract a tiny original parent at one shifted point.

    Dense tensor entries are read only at their recorded creation precision
    and their canonical integer coordinates are lifted. Lazy packet tensors
    are deliberately unsupported; this path is for original finite parents.
    It shares neither the production Cauchy evaluation nor the production
    half-edge contraction routine.
    """
    meter = None
    try:
        meter = _Meter(max_work, timeout_s)
        if type(max_edges) is not int or not 0 <= max_edges <= 8:
            raise ValueError("independent parent edge cap must be in 0..8")
        if not hasattr(network, "edges") or type(network.edges) is not int or network.edges > max_edges:
            raise OracleBudgetExceeded("parent exceeds independent half-edge oracle cap")
        L = source.get("L") if isinstance(source, dict) else None
        if type(L) is not int or L < 1 or L & (L - 1) or L > 8:
            raise ValueError("unsupported packet width")
        precision = certificate.get("precision")
        f = certificate.get("irreducible_polynomial")
        ring = _IndependentExtension(precision, f, meter)
        zeta = _read_coord(ring, certificate.get("zeta"))
        node = certificate.get("node")
        if type(node) is not int:
            raise ValueError("integer interpolation node required")
        alpha = 2 * L
        edges = source.get("edges")
        row_labels = source.get("row_labels")
        col_labels = source.get("column_labels")
        packets = source.get("packets")
        if not all(isinstance(value, (tuple, list)) for value in (edges, packets)):
            raise ValueError("source packet and edge sequences required")
        if not isinstance(row_labels, dict) or not isinstance(col_labels, dict):
            raise ValueError("source labels required")
        if tuple(tuple(edge) for edge in edges) != _independent_network_edges(network):
            raise ValueError("packet source edge IDs do not match the parent network")
        packet_entries = []
        assigned_edges = []
        for packet in packets:
            occupied = _packet_slots(packet, L, len(edges))
            assigned_edges.extend(edge_id for _, edge_id in occupied)
            rows = []
            cols = []
            for slot, edge_id in occupied:
                u, v = edges[edge_id]
                rows.append((slot, edge_id, row_labels[str(u)]))
                cols.append((slot, edge_id, col_labels[str(v)]))
            matrix = {}
            for x, rid, _ in rows:
                for y, cid, _ in cols:
                    polynomial = shifted_cauchy_polynomial(L, node, alpha, x, y, meter=meter)
                    matrix[(rid, cid)] = _evaluate_shifted(ring, polynomial, zeta)
            packet_entries.append((rows, cols, matrix))
        if sorted(assigned_edges) != list(range(len(edges))):
            raise ValueError("packet source does not partition parent edge IDs exactly once")

        vertex_tables = []
        for vertex in network.vertices:
            tensor = getattr(vertex, "tensor", None)
            entries = getattr(tensor, "entries", None)
            ports = getattr(vertex, "ports", None)
            if not isinstance(entries, tuple) or not isinstance(ports, tuple):
                raise OracleBudgetExceeded("independent parent oracle supports immutable dense tensors only")
            table = []
            for entry in entries:
                created_precision = getattr(entry, "creation_precision", None)
                defining_polynomial = getattr(entry, "defining_polynomial", None)
                coefficients = getattr(entry, "coefficients", None)
                if (type(created_precision) is not int or created_precision > precision or
                        defining_polynomial != f or not isinstance(coefficients, tuple) or
                        len(coefficients) != 1):
                    raise ValueError("tensor creation ring is incompatible with this point")
                # These are the stored creation-time representatives. Do not
                # reevaluate a recipe at the larger point precision.
                coordinates = _read_coord(ring, coefficients[0])
                if any(value >= (1 << created_precision) for value in coordinates):
                    raise ValueError("tensor entry is not canonical at its creation precision")
                table.append(ring.elem(coordinates))
            vertex_tables.append((vertex, ports, tuple(table)))

        total = ring.zero
        m = network.edges
        for xbits in product((0, 1), repeat=m):
            for ybits in product((0, 1), repeat=m):
                meter.tick()
                term = ring.one
                for vertex, ports, table in vertex_tables:
                    selected = ybits if vertex.side == "row" else xbits
                    index = sum(selected[edge] << i for i, edge in enumerate(ports))
                    term = ring.mul(term, table[index])
                    if term == ring.zero:
                        break
                if term != ring.zero:
                    for rows, cols, matrix in packet_entries:
                        for _, rid, _ in rows:
                            linear = ring.zero
                            for _, cid, _ in cols:
                                if xbits[cid]:
                                    linear = ring.add(linear, matrix[(rid, cid)])
                            factor = linear if ybits[rid] else ring.sub(ring.one, linear)
                            term = ring.mul(term, factor)
                            if term == ring.zero:
                                break
                        if term == ring.zero:
                            break
                total = ring.add(total, term)
        return {"valid": True, "status": "FINITE_INDEPENDENT_PARENT_POINT_CHECKED",
                "result": list(total), "node": node, "precision_bits": precision,
                "extension_degree": ring.e, "point": list(zeta),
                "parent_edges": m, "half_edge_assignments": 1 << (2 * m),
                "work_units": meter.used, "hard_memory_limit_enforced": False,
                "claim": "FINITE_DIRECT_HALF_EDGE_CONTRACTION_ONLY",
                "universal_theorem_proven": False}
    except OracleBudgetExceeded as exc:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT", "reason": str(exc),
                "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}
    except UnsupportedIntegralShift as exc:
        return {"valid": False, "status": "INCONCLUSIVE_UNSUPPORTED_INTEGRAL_SHIFT",
                "reason": str(exc), "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError,
            ZeroDivisionError, AttributeError) as exc:
        return {"valid": False, "status": "INVALID_INDEPENDENT_PARENT_POINT_INPUT",
                "reason": str(exc), "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}


def independent_tuple_coefficient(network, source, certificate, beta, *, max_edges=4,
                                  max_work=2_000_000, timeout_s=30.0):
    """Exhaustively compute one unpruned mode coefficient on a tiny parent.

    For each parent half-edge assignment, each packet row contributes either
    its local affine constant or exactly one targeted mode. The reference
    enumerates those row choices, filters for ``beta``, applies each source
    linear form, and sums over all half-edge assignments. This independent
    coefficient is useful for checking the unpruned and weighted-pruned sums
    against ``independent_parent_point`` on tiny networks.
    """
    meter = None
    try:
        mode_check = verify_point_mode_action(source, certificate,
                                              max_work=max_work,
                                              timeout_s=timeout_s)
        if mode_check.get("valid") is not True:
            return {"valid": False, "status": mode_check.get("status", "INVALID_CERTIFICATE"),
                    "reason": mode_check.get("reason", "independent mode action failed"),
                    "hard_memory_limit_enforced": False}
        meter = _Meter(max_work, timeout_s)
        if type(max_edges) is not int or not 0 <= max_edges <= 6:
            raise ValueError("tuple coefficient edge cap must be in 0..6")
        if not hasattr(network, "edges") or type(network.edges) is not int or network.edges > max_edges:
            raise OracleBudgetExceeded("parent exceeds independent tuple coefficient cap")
        L = source["L"]
        precision = certificate["precision"]
        f = certificate["irreducible_polynomial"]
        ring = _IndependentExtension(precision, f, meter)
        zeta = _read_coord(ring, certificate["zeta"])
        node = certificate["node"]
        modes = certificate["modes"]
        if (not isinstance(beta, (tuple, list)) or len(beta) != len(modes) or
                any(type(value) is not int or value < 0 for value in beta)):
            raise ValueError("beta must have one nonnegative exponent per mode")
        edges = source["edges"]
        row_labels = source["row_labels"]
        col_labels = source["column_labels"]
        if tuple(tuple(edge) for edge in edges) != _independent_network_edges(network):
            raise ValueError("packet source edge IDs do not match the parent network")
        rows_by_packet, cols_by_packet, cauchy_by_packet = [], [], []
        coordinate = _v2(node)
        alpha = 2 * L
        for packet in source["packets"]:
            occupied = _packet_slots(packet, L, len(edges))
            rows, cols, matrix = [], [], {}
            for slot, edge_id in occupied:
                u, v = edges[edge_id]
                rows.append((slot, edge_id, row_labels[str(u)][coordinate]))
                cols.append((slot, edge_id, col_labels[str(v)][coordinate]))
            for x, rid, row_group in rows:
                local = ring.zero
                for y, cid, col_group in cols:
                    polynomial = shifted_cauchy_polynomial(L, node, alpha, x, y, meter=meter)
                    value = _evaluate_shifted(ring, polynomial, zeta)
                    matrix[(rid, cid)] = value
                    if row_group == col_group:
                        local = ring.add(local, value)
                matrix[(rid, "local")] = local
            rows_by_packet.append(rows)
            cols_by_packet.append(cols)
            cauchy_by_packet.append(matrix)

        packet_modes = [[] for _ in source["packets"]]
        for mid, mode in enumerate(modes):
            pid = mode["packet"]
            if type(pid) is not int or not 0 <= pid < len(packet_modes):
                raise ValueError("mode packet identifier is invalid")
            row_values = {}
            for rid, encoded in mode["rows"]:
                if rid in row_values:
                    raise ValueError("duplicate mode row coefficient")
                row_values[rid] = _read_coord(ring, encoded[0])
            column_values = {}
            for cid, power in mode["column_terms"]:
                if cid in column_values or type(cid) is not int or type(power) is not int or power < 0:
                    raise ValueError("invalid or duplicate mode source term")
                column_values[cid] = power
            packet_modes[pid].append((mid, row_values, column_values))

        vertex_tables = []
        for vertex in network.vertices:
            tensor = getattr(vertex, "tensor", None)
            entries = getattr(tensor, "entries", None)
            ports = getattr(vertex, "ports", None)
            if not isinstance(entries, tuple) or not isinstance(ports, tuple):
                raise OracleBudgetExceeded("independent tuple oracle supports dense tensors only")
            table = []
            for entry in entries:
                if (entry.defining_polynomial != f or entry.creation_precision > precision or
                        len(entry.coefficients) != 1):
                    raise ValueError("parent tensor creation precision/ring mismatch")
                coordinates = _read_coord(ring, entry.coefficients[0])
                if any(value >= (1 << entry.creation_precision) for value in coordinates):
                    raise ValueError("parent entry is not canonical at creation precision")
                table.append(ring.elem(coordinates))
            vertex_tables.append((vertex, ports, tuple(table)))

        total = ring.zero
        m = network.edges
        for xbits in product((0, 1), repeat=m):
            for ybits in product((0, 1), repeat=m):
                meter.tick()
                term = ring.one
                for vertex, ports, table in vertex_tables:
                    selected = ybits if vertex.side == "row" else xbits
                    index = sum(selected[edge] << i for i, edge in enumerate(ports))
                    term = ring.mul(term, table[index])
                    if term == ring.zero:
                        break
                if term != ring.zero:
                    for pid, rows in enumerate(rows_by_packet):
                        mode_rows = packet_modes[pid]
                        target_ids = [mid for mid, _, _ in mode_rows]
                        row_options = []
                        for _, rid, _ in rows:
                            local = cauchy_by_packet[pid][(rid, "local")]
                            constant = local if ybits[rid] else ring.sub(ring.one, local)
                            options = [(None, constant)]
                            for mid, row_values, column_values in mode_rows:
                                if beta[mid] == 0 or rid not in row_values:
                                    continue
                                linear = ring.zero
                                for cid, power in column_values.items():
                                    if xbits[cid]:
                                        linear = ring.add(linear, ring.scalar(power))
                                coefficient = row_values[rid]
                                if not ybits[rid]:
                                    coefficient = ring.neg(coefficient)
                                options.append((mid, ring.mul(coefficient, linear)))
                            row_options.append(options)
                        packet_total = ring.zero
                        for selection in product(*row_options):
                            meter.tick()
                            counts = {mid: 0 for mid in target_ids}
                            product_value = ring.one
                            for mid, factor in selection:
                                product_value = ring.mul(product_value, factor)
                                if mid is not None:
                                    counts[mid] += 1
                            if all(counts[mid] == beta[mid] for mid in target_ids):
                                packet_total = ring.add(packet_total, product_value)
                        term = ring.mul(term, packet_total)
                        if term == ring.zero:
                            break
                total = ring.add(total, term)
        return {"valid": True, "status": "FINITE_UNPRUNED_TUPLE_COEFFICIENT_CHECKED",
                "beta": list(beta), "result": list(total),
                "half_edge_assignments": 1 << (2 * m),
                "work_units": meter.used, "precision_bits": precision,
                "hard_memory_limit_enforced": False,
                "claim": "FINITE_DIRECT_MODE_COEFFICIENT_ONLY",
                "universal_theorem_proven": False}
    except OracleBudgetExceeded as exc:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT", "reason": str(exc),
                "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}
    except UnsupportedIntegralShift as exc:
        return {"valid": False, "status": "INCONCLUSIVE_UNSUPPORTED_INTEGRAL_SHIFT",
                "reason": str(exc), "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError,
            ZeroDivisionError, AttributeError) as exc:
        return {"valid": False, "status": "INVALID_INDEPENDENT_TUPLE_INPUT",
                "reason": str(exc), "work_units": 0 if meter is None else meter.used,
                "hard_memory_limit_enforced": False}

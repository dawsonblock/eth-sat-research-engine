"""Independent direct Lagrange evaluation with explicit denominator loss."""
from veritas.research.independent_r82.point_mode_oracle import _IndependentExtension, _Meter
from veritas.research.parent_child_r98.model import canonical
from .degree_recovery import degree_points


def verify_degree_recovery(parent, layout, certificate, rows, claimed, *, budget, max_points=256):
    expected = tuple(degree_points(parent, layout, certificate, budget=budget, max_points=max_points))
    if len(rows) != len(expected):
        raise ValueError('independent degree grid incomplete')
    degree, alpha = certificate['degree_bound'], 2 << layout.a
    loss = (layout.a + 1) * degree
    results = []
    for start in range(0, len(expected), degree + 1):
        chunk = expected[start:start + degree + 1]
        t, _, precision = chunk[0]
        meter = _Meter(min(5_000_000, budget.policy.max_work - budget.work), min(60, budget.policy.max_seconds))
        ar = _IndependentExtension(precision, parent.defining_polynomial, meter,
                                  max_precision_bits=budget.policy.max_precision, max_extension_degree=12)
        total = ar.zero
        for i, (nt, point, bits) in enumerate(chunk):
            row = rows[start+i]
            if (canonical(row[:3]) != canonical((nt, point, bits)) or len(row[3]) != ar.e or
                    any(type(x) is not int or not 0 <= x < ar.modulus for x in row[3])):
                raise ValueError('independent degree point metadata or coordinates differ')
            numerator, denominator = ar.one, ar.one
            for j, (_, other, _) in enumerate(chunk):
                if i != j:
                    numerator = ar.mul(numerator, ar.sub(ar.elem([-t]), ar.mul(ar.elem([alpha]), other)))
                    denominator = ar.mul(denominator, ar.sub(point, other))
            total = ar.add(total, ar.mul(tuple(row[3]), ar.mul(numerator, ar.inverse(denominator))))
        if any(c % (1 << loss) for c in total):
            raise ValueError('independent Lagrange recovery is nonintegral')
        results.append(tuple((c >> loss) % (1 << parent.precision) for c in total))
        budget.tick(meter.used)
    if not results or any(canonical((value,)) != canonical(claimed) for value in results):
        raise ValueError('independent direct Lagrange recovery differs')
    return (results[0],)

"""An exact, bounded 2x2 instance of the paper's rectangle expansion.

This is a finite reference, not the paper's Network/Clique algorithm.
"""
from dataclasses import dataclass, field
from itertools import product

from .factors import CrossingFactor


@dataclass
class Ledger:
    additions: int = 0
    multiplications: int = 0
    table_reads: int = 0
    factor_reads: int = 0
    equality_checks: int = 0
    local_settings: int = 0
    exact_divisions: int = 0


@dataclass(frozen=True)
class GridResult:
    value: int
    numerator: int
    denominator: int
    modes: tuple
    ledger: Ledger = field(compare=False)


def _validate(width, tables):
    if width < 1 or len(tables) != 4:
        raise ValueError("expected positive width and four vertex tables")
    size = 1 << (3 * width)
    if any(len(table) != size for table in tables):
        raise ValueError("each table must have 2^(3*width) entries")
    if any(not isinstance(v, int) for table in tables for v in table):
        raise ValueError("vertex entries must be integers")


def _index(node, values, width):
    return sum(values[node, other] << (width * j)
               for j, other in enumerate(v for v in range(4) if v != node))


def direct_grid(width, tables, max_assignments=1_000_000):
    """Independent original clique contraction over the six edge strings."""
    _validate(width, tables)
    assignments = 1 << (6 * width)
    if assignments > max_assignments:
        raise ValueError("direct contraction exceeds max_assignments")
    edges = tuple((a, b) for a in range(4) for b in range(a + 1, 4))
    ledger, total = Ledger(), 0
    for bits in product(range(1 << width), repeat=6):
        values = {(a, b): z for (a, b), z in zip(edges, bits)}
        values.update({(b, a): z for (a, b), z in tuple(values.items())})
        term = 1
        for node in range(4):
            term *= tables[node][_index(node, values, width)]
            ledger.table_reads += 1
            ledger.multiplications += 1
        total += term
        ledger.additions += 1
        ledger.local_settings += 1
    return total, ledger


def rectangle_grid(width, tables, max_local_settings=1_000_000, orientation="cheapest"):
    """Contract each rectangle mode using its globally cheaper orientation.

    Limits bound local settings, not time, memory, or individual bit operations.
    Ledger arithmetic counts only outer contraction operations; factor-reader
    internals and Python integer bit costs are not included.
    """
    _validate(width, tables)
    if orientation not in ("cheapest", "row", "column"):
        raise ValueError("orientation must be cheapest, row, or column")
    t = (width + 2) // 3
    plans = []
    for i in range(t + 1):
        row, col = CrossingFactor(width, i, "row"), CrossingFactor(width, i, "column")
        factor = (row if orientation == "row" else col if orientation == "column"
                  else row if row.bits <= col.bits else col)
        plans.append(factor)
    estimate = sum(2 * (1 << (2 * width + f.bits + 6 * width)) for f in plans)
    if estimate > max_local_settings:
        raise ValueError(f"rectangle contraction needs {estimate} local settings, exceeds limit")
    ledger, modes = Ledger(), []
    mask = (1 << width) - 1
    for factor in plans:
        row = factor.direction == "row"
        groups = ((0, 1), (2, 3)) if row else ((0, 2), (1, 3))
        straight = ((0, 2), (1, 3)) if row else ((0, 1), (2, 3))
        subtotal = 0
        for interface in range(1 << (2 * width + factor.bits)):
            straight_values = (interface & mask, (interface >> width) & mask)
            theta = interface >> (2 * width)
            sums = []
            for side, group in enumerate(groups):
                local_sum = 0
                slots = tuple((node, other) for node in group for other in range(4) if other != node)
                for assignment in range(1 << (6 * width)):
                    ledger.local_settings += 1
                    values = {slot: (assignment >> (j * width)) & mask for j, slot in enumerate(slots)}
                    ledger.equality_checks += 1
                    if values[group[0], group[1]] != values[group[1], group[0]]:
                        continue
                    matches = True
                    for (a, b), z in zip(straight, straight_values):
                        ledger.equality_checks += 1
                        if values[(a if side == 0 else b), (b if side == 0 else a)] != z:
                            matches = False
                            break
                    if not matches:
                        continue
                    if row:
                        boundary = (values[0, 3], values[1, 2]) if side == 0 else (values[2, 1], values[3, 0])
                    else:
                        boundary = (values[0, 3], values[2, 1]) if side == 0 else (values[1, 2], values[3, 0])
                    f = factor.evaluate(boundary if side == 0 else (0, 0),
                                        boundary if side == 1 else (0, 0), theta)[side]
                    ledger.factor_reads += 1
                    term = f
                    for node in group:
                        term *= tables[node][_index(node, values, width)]
                        ledger.multiplications += 1
                        ledger.table_reads += 1
                    local_sum += term
                    ledger.additions += 1
                sums.append(local_sum)
            subtotal += sums[0] * sums[1]
            ledger.multiplications += 1
            ledger.additions += 1
        modes.append((factor.degree, factor.direction, factor.bits, subtotal))
    numerator = sum(m[3] for m in modes)
    ledger.additions += len(modes)
    denominator = 1 << t
    value, remainder = divmod(numerator, denominator)
    ledger.exact_divisions += 1
    if remainder:
        raise ArithmeticError("rectangle reconstruction was not exactly divisible")
    return GridResult(value, numerator, denominator, tuple(modes), ledger)

"""Auxiliary coordinates, the swap matrix `M_0`, measurements `C^B`, rows `P_u`.

Paper objects (vendored in `paper/`):

* `subsec:incidence-layout` (l. 2094-2159) -- the label set
  `B = ([r]^Q)^2`, its groups `S^B_{t,g}`, and the goal for the rows.
* `eq:swap-weight` and `eq:swap-matrix-definition` (l. 2186-2228) --
  `V_0`, `W_0`, `f_I`, `M_0 = V_0 f_I(W_0)`.
* `lem:swaps-matrix` (l. 2230-2267) -- the measurement matrix `C^B`.
* `lem:swaps-support` (l. 2288-2308) -- the `R-1` mismatch bound.
* `eq:coefficient-correction` and `eq:swaps-row` (l. 2318-2335) --
  `phi_{u,y}` and the rows `P_u(T)`.

An index of `B` is a tuple of `Q` pairs `(a_u(s), d_u(s))` in `[r]^2`. It is
encoded as an integer with pair `s` in base `r^2`, pair `0` least
significant, so that swapping pair `s` is an arithmetic operation on the
encoded index.

`M_0` is stored as a sparse linear combination of the permutation matrices
`Pi_[Q]\\S`, obtained from the Walsh--Hadamard transform of `j -> f_I(j)`.
Only `|S| <= R-1` have a nonzero coefficient, which is exactly
`lem:swaps-support`. The transform is computed exactly over `Fraction` and
the bound is checked rather than assumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product


def _perm_mask(mask: int, r: int, Q: int) -> tuple:
    """Permutation array for `Pi_T` with `T` the set bits of `mask`."""
    radix = r * r
    size = radix ** Q
    powers = [radix ** s for s in range(Q)]
    result = []
    for index in range(size):
        moved = index
        for s in range(Q):
            if mask >> s & 1:
                pair = (index // powers[s]) % radix
                a, d = divmod(pair, r)
                moved += (d * r + a - pair) * powers[s]
        result.append(moved)
    return tuple(result)


def _decode(index: int, r: int, Q: int) -> tuple:
    radix = r * r
    pairs = []
    for _ in range(Q):
        index, pair = divmod(index, radix)
        pairs.append(divmod(pair, r))
    return tuple(pairs)


def _encode(pairs, r: int) -> int:
    radix = r * r
    index = 0
    for a, d in reversed(pairs):
        index = index * radix + (a * r + d)
    return index


def _fwht(values):
    """In-place Walsh--Hadamard transform, kernel `(-1)**popcount(S & S')`."""
    size = len(values)
    step = 1
    while step < size:
        for start in range(0, size, 2 * step):
            for offset in range(step):
                left = start + offset
                right = left + step
                a, b = values[left], values[right]
                values[left], values[right] = a + b, a - b
        step *= 2
    return values


def _binomial_polynomial(R: int, A0: int):
    """`f_I(z) = (-1)**A0 * sum_{j<R} (-2)**j * C(z-A0, j)` as coefficients."""
    total = [Fraction(0)] * R
    term = [Fraction(1)]                      # C(z-A0, 0)
    sign = Fraction(1 if A0 % 2 == 0 else -1)
    for j in range(R):
        weight = sign * Fraction((-2) ** j)
        for degree, coefficient in enumerate(term):
            total[degree] += weight * coefficient
        # term <- term * (z - A0 - j) / (j + 1)
        shifted = [Fraction(0)] * (len(term) + 1)
        for degree, coefficient in enumerate(term):
            shifted[degree + 1] += coefficient
            shifted[degree] -= (A0 + j) * coefficient
        term = [coefficient / (j + 1) for coefficient in shifted]
    return tuple(total)


def _phi_minus_one(points) -> tuple:
    """`prod_{s in points}(1 - T/s) - 1`, as a coefficient tuple."""
    poly = [Fraction(1)]
    for s in sorted(points):
        nxt = [Fraction(0)] * (len(poly) + 1)
        for degree, coefficient in enumerate(poly):
            nxt[degree] += coefficient
            nxt[degree + 1] -= coefficient / s
        poly = nxt
    poly[0] -= 1
    return tuple(poly)


def _pair_support(kind, a, b):
    if kind == 'diag':
        return (((a, a), 1),)
    if kind == 'sym':
        return (((a, b), 1), ((b, a), 1))
    return (((a, b), 1), ((b, a), -1))


@dataclass(frozen=True)
class AuxiliaryLayout:
    """The auxiliary array of `subsec:incidence-layout` for one parameter set."""

    r: int
    Q: int
    R: int
    A0: int
    D: int
    terms: tuple               # ((Fraction c_S, tuple permutation), ...)
    measurement_rows: tuple    # tuple of {index: 1 or -1}
    polynomial: tuple          # f_I coefficients

    def __post_init__(self):
        if self.D != self.r ** (2 * self.Q):
            raise ValueError('D must equal r**(2Q)')
        if len(self.polynomial) != self.R:
            raise ValueError('f_I must have degree at most R-1')

    # -- index arithmetic ---------------------------------------------------

    def decode(self, index):
        return _decode(index, self.r, self.Q)

    def encode(self, pairs):
        return _encode(pairs, self.r)

    def group_of(self, index, point):
        """`a_u(point)`: the group containing coordinate `u` at `point`."""
        return self.decode(index)[point][0]

    def assigned_group(self, index, point):
        """`d_u(point)`: the group the row indexed by `u` is assigned to."""
        return self.decode(index)[point][1]

    def group_members(self, point, group):
        return tuple(index for index in range(self.D)
                     if self.group_of(index, point) == group)

    # -- the matrix M_0 -----------------------------------------------------

    def matrix_entry(self, row, column):
        """`M_0[row, column]`, summed over the permutation terms."""
        total = Fraction(0)
        for coefficient, permutation in self.terms:
            if permutation[row] == column:
                total += coefficient
        return total

    def matrix_row(self, row):
        """Sparse row of `M_0`: `{column: coefficient}`."""
        result = {}
        for coefficient, permutation in self.terms:
            column = permutation[row]
            result[column] = result.get(column, Fraction(0)) + coefficient
        return {column: value for column, value in result.items() if value}

    def apply_matrix(self, vector):
        """`M_0 @ vector` for a sparse `{index: value}` vector."""
        result = {}
        for index, value in vector.items():
            for coefficient, permutation in self.terms:
                column = permutation[index]
                result[column] = result.get(column, Fraction(0)) + coefficient * value
        return {column: total for column, total in result.items() if total}

    def mismatch_set(self, row, column):
        """`E_{u,y} = {s in [Q] : a_y(s) != d_u(s)}`, with `[Q] = {1..Q}`.

        The paper indexes evaluation points by `1..Q`, and `phi_{u,y}` divides
        by those point numbers, so this returns one-based positions.
        """
        left, right = self.decode(row), self.decode(column)
        return tuple(s + 1 for s in range(self.Q) if right[s][0] != left[s][1])

    def row_polynomial(self, row):
        """`P_u(T)` as `{column: coefficient tuple}` (`eq:swaps-row`).

        Uses `P_u = delta_u + M_0[u,y] (phi_{u,y}(T) - 1)`, the paper's
        decomposition with the two `M_0[u,y] delta_y` terms merged.
        """
        result = {row: (Fraction(1),)}
        for column, coefficient in self.matrix_row(row).items():
            correction = _phi_minus_one(self.mismatch_set(row, column))
            current = result.get(column, ())
            length = max(len(current), len(correction))
            merged = [Fraction(0)] * length
            for degree, value in enumerate(current):
                merged[degree] += value
            for degree, value in enumerate(correction):
                merged[degree] += coefficient * value
            while merged and merged[-1] == 0:
                merged.pop()
            result[column] = tuple(merged)
        return {column: value for column, value in result.items() if value}

    def evaluate_row(self, row, point):
        """`P_u(point)` as a sparse `{column: Fraction}`."""
        result = {}
        for column, coefficients in self.row_polynomial(row).items():
            value = Fraction(0)
            power = Fraction(1)
            for coefficient in coefficients:
                value += coefficient * power
                power *= point
            if value:
                result[column] = value
        return result

    # -- the measurement matrix C^B ----------------------------------------

    def basis_choices(self):
        """Every tuple of per-position eigenvector choices."""
        options = []
        for _ in range(self.Q):
            per_position = [('diag', a, None) for a in range(self.r)]
            per_position += [('sym', a, b) for a in range(self.r)
                             for b in range(a + 1, self.r)]
            per_position += [('anti', a, b) for a in range(self.r)
                             for b in range(a + 1, self.r)]
            options.append(per_position)
        return product(*options)

    def basis_vector(self, choices):
        """Sparse `{index: value}` for one tensor-product eigenvector."""
        supports = [_pair_support(*choice) for choice in choices]
        result = {}
        for pairs in product(*supports):
            index = _encode([pair for pair, _ in pairs], self.r)
            value = 1
            for _, weight in pairs:
                value *= weight
            if value:
                result[index] = value
        return result

    def negatives_of(self, choices):
        """`j`: the number of positions with eigenvalue `-1`."""
        return sum(1 for choice in choices if choice[0] == 'anti')

    def measurement_matrix(self):
        """Rows of `C^B`: transposes of the basis vectors with `j not in I`."""
        interval = self.interval
        rows = []
        for choices in self.basis_choices():
            if self.negatives_of(choices) in interval:
                continue
            rows.append(self.basis_vector(choices))
        return tuple(rows)

    # -- checks -------------------------------------------------------------

    @property
    def interval(self):
        return tuple(range(self.A0, self.A0 + self.R))

    def check_support_bound(self):
        """`lem:swaps-support`: nonzero entries mismatch in at most `R-1` points."""
        worst = 0
        for row in range(self.D):
            for column in self.matrix_row(row):
                worst = max(worst, len(self.mismatch_set(row, column)))
        return worst <= self.R - 1

    def check_kernel_fixed(self):
        """`lem:swaps-matrix`: `M_0` fixes every basis vector with `j in I`."""
        for choices in self.basis_choices():
            if self.negatives_of(choices) not in self.interval:
                continue
            vector = self.basis_vector(choices)
            image = self.apply_matrix(vector)
            if image != vector:
                return False
        return True

    def check_row_normalisation(self):
        """`P_u(0) = delta_u` for every row (`lem:swaps-forms`)."""
        for row in range(self.D):
            if self.evaluate_row(row, 0) != {row: Fraction(1)}:
                return False
        return True

    def check_degree_bound(self):
        """Every row has `deg P_u <= R-1`."""
        for row in range(self.D):
            for coefficients in self.row_polynomial(row).values():
                if len(coefficients) > self.R:
                    return False
        return True


def build_auxiliary_layout(parameters, *, max_terms=4096) -> AuxiliaryLayout:
    """Construct `M_0`, `C^B` and the auxiliary rows for one parameter set."""
    r, Q, R, A0 = parameters.r, parameters.Q, parameters.R, parameters.A0
    polynomial = _binomial_polynomial(R, A0)
    values = []
    for mask in range(1 << Q):
        j = bin(mask).count('1')
        value = Fraction(0)
        power = Fraction(1)
        for coefficient in polynomial:
            value += coefficient * power
            power *= j
        values.append(value)
    transformed = _fwht(values)
    scale = Fraction(1, 1 << Q)
    terms = []
    for mask in range(1 << Q):
        coefficient = transformed[mask] * scale
        if not coefficient:
            continue
        # The character indexed by `mask` multiplies `Pi_mask`; multiplying by
        # `V_0 = Pi_[Q]` leaves `Pi_[Q] \\ mask`.
        swap_mask = ((1 << Q) - 1) ^ mask
        terms.append((coefficient, _perm_mask(swap_mask, r, Q)))
    if len(terms) > max_terms:
        raise ValueError('M_0 expansion exceeds the finite reference budget')
    empty = AuxiliaryLayout(r=r, Q=Q, R=R, A0=A0, D=r ** (2 * Q),
                            terms=tuple(terms), measurement_rows=(),
                            polynomial=polynomial)
    rows = empty.measurement_matrix()
    return AuxiliaryLayout(r=r, Q=Q, R=R, A0=A0, D=empty.D, terms=tuple(terms),
                           measurement_rows=rows, polynomial=polynomial)

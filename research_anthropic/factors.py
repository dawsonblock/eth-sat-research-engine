"""Lazy factorizations from Lemma 2(b), with explicit index bits."""
from dataclasses import dataclass

from .eight_square import crossing_coefficients, crossing_col, crossing_row, psi


@dataclass(frozen=True)
class CrossingFactor:
    width: int
    degree: int
    direction: str

    def __post_init__(self):
        if self.width < 1 or self.direction not in ("row", "column"):
            raise ValueError("width must be positive and direction row or column")
        if not 0 <= self.degree <= self.blocks:
            raise ValueError("coefficient degree out of range")

    @property
    def blocks(self):
        return (self.width + 2) // 3

    @property
    def compressed_bits(self):
        t, i = self.blocks, self.degree
        return 4 * t + 3 * i if self.direction == "row" else 7 * t - 3 * i

    @property
    def bits(self):
        return min(2 * self.width, self.compressed_bits)

    @property
    def direct(self):
        return 2 * self.width <= self.compressed_bits

    def evaluate(self, left, right, theta):
        """Return the two integer factors at one index, without materializing tables.

        Row inputs are (x,y),(u,v); column inputs are (x,u),(y,v).
        The direct fallback indexes the entire left boundary. Otherwise theta
        contains the t-bit set Q followed by 3- or 6-bit block indices.
        """
        limit = 1 << self.width
        if len(left) != 2 or len(right) != 2 or any(not 0 <= a < limit for a in (*left, *right)):
            raise ValueError("boundary values must fit the specified width")
        if not 0 <= theta < 1 << self.bits:
            raise ValueError("index does not fit factorization")
        if self.direct:
            a, b = theta & (limit - 1), theta >> self.width
            if self.direction == "row":
                x, y, u, v = a, b, *right
            else:
                x, u, y, v = a, b, *right
            return int(left == (a, b)), crossing_coefficients(x, y, u, v, self.width)[self.degree]

        subset = theta & ((1 << self.blocks) - 1)
        if subset.bit_count() != self.degree:
            return 0, 0
        offset = self.blocks
        first = second = 1
        for block in range(self.blocks):
            a, b = ((v >> (3 * block)) & 7 for v in left)
            c, d = ((v >> (3 * block)) & 7 for v in right)
            is_col = bool((subset >> block) & 1)
            aligned = is_col == (self.direction == "column")
            if aligned:
                k = (theta >> offset) & 7
                offset += 3
                first *= psi(k, a, b)
                second *= psi(k, d, c)
            else:
                encoded = (theta >> offset) & 63
                offset += 6
                aa, bb = encoded & 7, encoded >> 3
                first *= int((a, b) == (aa, bb))
                if self.direction == "row":
                    second *= crossing_col(aa, bb, c, d)
                else:
                    second *= crossing_row(aa, c, bb, d)
        return first, second

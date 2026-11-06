"""Canonical, strictly validated CNF. All declared variables (including unused) count."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json

MAX_VARS = 512
MAX_CLAUSES = 20_000
MAX_LITERALS = 200_000


@dataclass(frozen=True)
class CNF:
    n: int
    clauses: tuple[tuple[int, ...], ...]

    def __post_init__(self):
        if type(self.n) is not int or not (0 <= self.n <= MAX_VARS):
            raise ValueError(f"n must be an integer in 0..{MAX_VARS}")
        if not isinstance(self.clauses, (tuple, list)):
            raise ValueError('clauses must be a list or tuple')
        if len(self.clauses) > MAX_CLAUSES:
            raise ValueError("too many clauses")
        size = 0
        for clause in self.clauses:
            if not isinstance(clause, (tuple, list)):
                raise ValueError('each clause must be a list or tuple')
            size += len(clause)
            if size > MAX_LITERALS:
                raise ValueError("too many literals")
            for lit in clause:
                if type(lit) is not int or lit == 0 or abs(lit) > self.n:
                    raise ValueError(f"bad literal {lit!r} for n={self.n}")
        # A frozen dataclass is not immutable if it retains mutable lists.
        object.__setattr__(self, 'clauses', tuple(tuple(c) for c in self.clauses))

    @classmethod
    def from_lists(cls, n: int, clauses: list[list[int]]) -> "CNF":
        if not isinstance(clauses, list):
            raise ValueError("clauses must be a list")
        if any(not isinstance(c, list) for c in clauses):
            raise ValueError("each clause must be a list")
        return cls(n, tuple(tuple(c) for c in clauses))

    def as_dict(self) -> dict:
        return {"n": self.n, "clauses": [list(c) for c in self.clauses]}

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def evaluate(self, model: dict[int, bool]) -> bool:
        if any(v not in model or type(model[v]) is not bool for v in range(1, self.n + 1)):
            raise ValueError("complete Boolean assignment required")
        return all(any(model[abs(l)] if l > 0 else not model[abs(l)] for l in c) for c in self.clauses)

    def to_dimacs(self) -> str:
        return f"p cnf {self.n} {len(self.clauses)}\n" + "".join(" ".join(map(str, c)) + (" " if c else "") + "0\n" for c in self.clauses)

    @classmethod
    def from_dimacs(cls, text: str) -> "CNF":
        if len(text) > 1_500_000:
            raise ValueError("DIMACS too large")
        header = None
        clauses: list[tuple[int, ...]] = []
        current: list[int] = []
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("c"):
                continue
            if s.startswith("p"):
                bits = s.split()
                if header is not None or len(bits) != 4 or bits[0:2] != ["p", "cnf"]:
                    raise ValueError("invalid/duplicate DIMACS header")
                try:
                    n, m = int(bits[2]), int(bits[3])
                except ValueError as exc:
                    raise ValueError("invalid DIMACS header counts") from exc
                if n < 0 or m < 0 or n > MAX_VARS or m > MAX_CLAUSES:
                    raise ValueError("DIMACS dimensions out of range")
                header = (n, m)
                continue
            if header is None:
                raise ValueError("DIMACS header must precede clauses")
            for token in s.split():
                try:
                    lit = int(token)
                except ValueError as exc:
                    raise ValueError(f"invalid literal {token!r}") from exc
                if lit == 0:
                    clauses.append(tuple(current))
                    current = []
                    if len(clauses) > header[1]:
                        raise ValueError("too many DIMACS clauses")
                else:
                    if abs(lit) > header[0]:
                        raise ValueError("literal exceeds declared variables")
                    current.append(lit)
                    if len(current) > MAX_LITERALS:
                        raise ValueError("clause too long")
        if header is None or current or len(clauses) != header[1]:
            raise ValueError("missing header, unterminated clause, or wrong clause count")
        return cls(header[0], tuple(clauses))

    def with_extra_clauses(self, extra: list[list[int]]) -> "CNF":
        return CNF(self.n, self.clauses + tuple(tuple(c) for c in extra))

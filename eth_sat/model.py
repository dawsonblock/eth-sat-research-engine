"""Small immutable CNF model and DIMACS parser."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Literal:
    """A one-based variable index and whether the literal is negated."""

    variable: int
    negated: bool = False

    def __post_init__(self) -> None:
        if self.variable < 1:
            raise ValueError("literal variables are one-based positive integers")

    def value(self, bit: int | bool) -> bool:
        return bool(bit) != self.negated


Clause = tuple[Literal, ...]


@dataclass(frozen=True, slots=True)
class CNF:
    """A CNF over an explicitly declared number of variables."""

    num_variables: int
    clauses: tuple[Clause, ...]

    def __post_init__(self) -> None:
        if self.num_variables < 0:
            raise ValueError("num_variables must be nonnegative")
        normalized = tuple(tuple(clause) for clause in self.clauses)
        for clause in normalized:
            for literal in clause:
                if literal.variable > self.num_variables:
                    raise ValueError(
                        f"variable {literal.variable} exceeds declared variable count "
                        f"{self.num_variables}"
                    )
        object.__setattr__(self, "clauses", normalized)

    @classmethod
    def from_dimacs(cls, source: str | Path) -> "CNF":
        """Parse DIMACS text or a path to a DIMACS file."""
        if isinstance(source, Path):
            text = source.read_text(encoding="utf-8")
        elif "\n" not in source and "\r" not in source:
            candidate = Path(source)
            try:
                is_file = candidate.is_file()
            except OSError:
                is_file = False
            text = candidate.read_text(encoding="utf-8") if is_file else source
        else:
            text = source

        declared_variables: int | None = None
        declared_clauses: int | None = None
        literals: list[int] = []
        clauses: list[Clause] = []
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                if declared_variables is not None:
                    raise ValueError(f"duplicate DIMACS problem line at line {line_number}")
                fields = line.split()
                if len(fields) != 4 or fields[:2] != ["p", "cnf"]:
                    raise ValueError(f"invalid DIMACS problem line at line {line_number}")
                declared_variables, declared_clauses = int(fields[2]), int(fields[3])
                if declared_variables < 0 or declared_clauses < 0:
                    raise ValueError("DIMACS counts must be nonnegative")
                continue
            if declared_variables is None:
                raise ValueError(f"DIMACS data precedes problem line at line {line_number}")
            try:
                values = [int(field) for field in line.split()]
            except ValueError as exc:
                raise ValueError(f"invalid integer at DIMACS line {line_number}") from exc
            for value in values:
                if value == 0:
                    clauses.append(
                        tuple(Literal(abs(item), item < 0) for item in literals)
                    )
                    literals.clear()
                else:
                    if abs(value) > declared_variables:
                        raise ValueError(
                            f"literal {value} exceeds declared variable count at line {line_number}"
                        )
                    literals.append(value)
        if declared_variables is None:
            raise ValueError("missing DIMACS problem line")
        if literals:
            raise ValueError("last DIMACS clause is missing its terminating zero")
        if declared_clauses != len(clauses):
            raise ValueError(
                f"DIMACS declares {declared_clauses} clauses but contains {len(clauses)}"
            )
        return cls(declared_variables, tuple(clauses))

    @classmethod
    def from_signed_clauses(
        cls, num_variables: int, clauses: Iterable[Iterable[int]]
    ) -> "CNF":
        """Build from clauses whose signed integers use DIMACS polarity."""
        return cls(
            num_variables,
            tuple(
                tuple(Literal(abs(value), value < 0) for value in clause)
                for clause in clauses
            ),
        )

    def to_dimacs(self) -> str:
        lines = [f"p cnf {self.num_variables} {len(self.clauses)}"]
        for clause in self.clauses:
            values = [
                -literal.variable if literal.negated else literal.variable
                for literal in clause
            ]
            lines.append(" ".join(map(str, values + [0])))
        return "\n".join(lines) + "\n"

    def is_satisfied(self, assignment: Iterable[int | bool]) -> bool:
        bits = tuple(bool(bit) for bit in assignment)
        if len(bits) != self.num_variables:
            raise ValueError("assignment length does not match declared variable count")
        return all(
            any(literal.value(bits[literal.variable - 1]) for literal in clause)
            for clause in self.clauses
        )

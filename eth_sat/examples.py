"""Tiny CNF instances shipped with the package."""

from .model import CNF


def simple() -> CNF:
    """Three-variable formula with exactly four satisfying assignments."""
    return CNF.from_signed_clauses(3, ((1, 2), (-1, 3)))

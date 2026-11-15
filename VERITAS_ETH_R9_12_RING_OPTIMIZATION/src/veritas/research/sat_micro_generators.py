"""Seeded tiny 3-CNF generators for residual-compression micro-benchmarks."""
from __future__ import annotations

import random
from typing import Literal

from veritas.core.cnf import CNF

FamilyKind = Literal["coupled", "adversarial"]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def coupled_chain_3cnf(n: int, seed: int) -> tuple[str, CNF]:
    """Variables on a path: each clause uses consecutive triples (coupled)."""
    if not 3 <= n <= 10:
        raise ValueError("coupled_chain_3cnf requires n in 3..10")
    r = _rng(seed)
    clauses: list[list[int]] = []
    for i in range(1, n - 1):
        triple = [i, i + 1, i + 2]
        clause = [v if r.random() < 0.5 else -v for v in triple]
        clauses.append(clause)
    # close triangle at end for extra coupling
    if n >= 4:
        triple = [n - 2, n - 1, n]
        clauses.append([v if r.random() < 0.5 else -v for v in triple])
    name = f"coupled_chain_n{n}_s{seed}"
    return name, CNF.from_lists(n, clauses)


def adversarial_random_3cnf(n: int, seed: int, *, m: int | None = None) -> tuple[str, CNF]:
    """Dense random 3-CNF (many distinct residuals expected; not a hardness proof)."""
    if not 3 <= n <= 10:
        raise ValueError("adversarial_random_3cnf requires n in 3..10")
    r = _rng(seed)
    m_clauses = m if m is not None else max(n, min(4 * n, 24))
    clauses: list[list[int]] = []
    for _ in range(m_clauses):
        vars = r.sample(range(1, n + 1), 3)
        clauses.append([v if r.random() < 0.5 else -v for v in vars])
    name = f"adversarial_rand_n{n}_m{m_clauses}_s{seed}"
    return name, CNF.from_lists(n, clauses)


def adversarial_tight_triangle(n: int, seed: int) -> tuple[str, CNF]:
    """Overlapping 3-cliques on {1..n} (high coupling, low residual merge hope)."""
    if not 3 <= n <= 8:
        raise ValueError("adversarial_tight_triangle requires n in 3..8")
    r = _rng(seed)
    clauses: list[list[int]] = []
    for i in range(1, n - 1):
        for j in range(i + 1, n):
            if j + 1 <= n:
                triple = [i, j, j + 1]
                clauses.append([v if r.random() < 0.5 else -v for v in triple])
    name = f"adversarial_tri_cliques_n{n}_s{seed}"
    return name, CNF.from_lists(n, clauses[: min(len(clauses), 28)])


def adversarial_grid_cases(
    *,
    n_min: int = 6,
    n_max: int = 10,
    seeds: tuple[int, ...] = (0, 1, 2),
) -> tuple[tuple[str, CNF, FamilyKind], ...]:
    """Research grid (not CI-pinned): random adversarial 3-CNFs, seeds per n."""
    if not 3 <= n_min <= n_max <= 10:
        raise ValueError("adversarial_grid_cases requires 3 <= n_min <= n_max <= 10")
    out: list[tuple[str, CNF, FamilyKind]] = []
    for n in range(n_min, n_max + 1):
        for seed in seeds:
            name, cnf = adversarial_random_3cnf(n, seed)
            out.append((name, cnf, "adversarial"))
    return tuple(out)


def micro_generator_suite() -> tuple[tuple[str, CNF, FamilyKind], ...]:
    """Pinned MICRO tier cases for CI (small n)."""
    out: list[tuple[str, CNF, FamilyKind]] = []
    for seed in (0, 1, 2):
        name, cnf = coupled_chain_3cnf(5, seed)
        out.append((name, cnf, "coupled"))
    for seed in (0, 1):
        name, cnf = adversarial_random_3cnf(5, seed, m=12)
        out.append((name, cnf, "adversarial"))
    name, cnf = adversarial_tight_triangle(5, 0)
    out.append((name, cnf, "adversarial"))
    return tuple(out)
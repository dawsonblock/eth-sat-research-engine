"""Differential tests: every exact-counting route against an independent brute force.

The oracle below is deliberately self-contained (no imports from ``veritas`` counters),
so a bug shared by the engine and its in-tree "reference" cannot hide.  Inputs are small
(n <= 7) and seeded, so failures are reproducible and the whole module runs in seconds.

These tests exist because the shipped per-feature tests only used clean, hand-picked
formulas.  Explicit empty clauses, empty/unary XOR equations and preprocessing-induced
renumbering were never exercised and produced silently wrong counts.
"""
from __future__ import annotations

import random

from veritas.core.cnf import CNF
from veritas.research.cnf_preprocess import count_preserving_preprocess
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.gf2_xor_count import (
    XorEquation,
    count_pure_xor,
    structure_with_optional_xor,
)
from veritas.research.gf2_xor_encode import count_via_xor_encoding, encode_xor_equations
from veritas.research.gf2_xor_mixed import count_mixed_xor_cnf
from veritas.research.gf2_xor_substitute import (
    apply_xor_unary_units,
    substitute_binary_xor,
    try_xor_algebraic_reduce,
)
from veritas.research.hybrid_router import hybrid_count


# --------------------------------------------------------------------------- oracle
def brute(n: int, clauses, xors=()) -> int:
    """Count assignments of x1..xn satisfying all clauses and all XOR equations."""
    total = 0
    for bits in range(1 << n):
        ok = True
        for cl in clauses:
            if not any((((bits >> (abs(l) - 1)) & 1) == 1) == (l > 0) for l in cl):
                ok = False
                break
        if not ok:
            continue
        for variables, rhs in xors:
            parity = 0
            for v in variables:
                parity ^= (bits >> (v - 1)) & 1
            if parity != (rhs & 1):
                ok = False
                break
        if ok:
            total += 1
    return total


def brute_cnf(cnf: CNF) -> int:
    return brute(cnf.n, cnf.clauses)


def brute_mixed(cnf: CNF, eqs) -> int:
    return brute(cnf.n, cnf.clauses, [(e.variables, e.rhs) for e in eqs])


# ------------------------------------------------------------------------ generators
def random_cnf(rng: random.Random, *, n_max=7, allow_empty_clause=True) -> CNF:
    n = rng.randint(1, n_max)
    clauses = []
    for _ in range(rng.randint(0, 6)):
        length = rng.choice([0, 1, 1, 2, 2, 3, 3]) if allow_empty_clause else rng.choice([1, 1, 2, 2, 3, 3])
        clauses.append([rng.choice([-1, 1]) * rng.randint(1, n) for _ in range(length)])
    return CNF.from_lists(n, clauses)


def random_xors(rng: random.Random, n: int, *, allow_empty=True) -> tuple[XorEquation, ...]:
    eqs = []
    for _ in range(rng.randint(0, 4)):
        low = 0 if allow_empty else 1
        size = rng.randint(low, min(n, 4))
        eqs.append(XorEquation(tuple(rng.sample(range(1, n + 1), size)), rng.randint(0, 1)))
    return tuple(eqs)


def _report(name, failures):
    assert not failures, f"{name}: {len(failures)} wrong counts, first: {failures[:3]}"


def _fmt(cnf: CNF, eqs=()):
    return {
        'n': cnf.n,
        'clauses': [list(c) for c in cnf.clauses],
        'xors': [(list(e.variables), e.rhs) for e in eqs],
    }


# ----------------------------------------------------------- pure-CNF routes (no XOR)
def test_preprocess_preserves_count_including_empty_clauses():
    rng = random.Random(20260101)
    failures = []
    for _ in range(600):
        cnf = random_cnf(rng)
        truth = brute_cnf(cnf)
        simplified, report = count_preserving_preprocess(cnf)
        got = 0 if report.empty_clause else brute_cnf(simplified)
        if got != truth:
            failures.append((_fmt(cnf), got, truth))
    _report('count_preserving_preprocess', failures)


def test_structure_and_hybrid_counts_match_brute_force():
    rng = random.Random(20260102)
    failures = []
    for _ in range(300):
        cnf = random_cnf(rng)
        truth = brute_cnf(cnf)
        for label, run in (
            ('hybrid', lambda c: hybrid_count(c)),
            ('structure/pre=False', lambda c: structure_aware_count(c, preprocess=False, timeout_s=5)),
            ('structure/pre=True', lambda c: structure_aware_count(c, preprocess=True, timeout_s=5)),
        ):
            got = int(run(cnf)['count'])
            if got != truth:
                failures.append((label, _fmt(cnf), got, truth))
    _report('CNF routes', failures)


# ----------------------------------------------------------------- pure-XOR / encoding
def test_pure_xor_count_matches_brute_force():
    rng = random.Random(20260103)
    failures = []
    for _ in range(400):
        n = rng.randint(1, 7)
        eqs = random_xors(rng, n)
        truth = brute(n, [], [(e.variables, e.rhs) for e in eqs])
        got = count_pure_xor(eqs, n)
        if got != truth:
            failures.append((n, [(e.variables, e.rhs) for e in eqs], got, truth))
    _report('count_pure_xor', failures)


def test_xor_cnf_encoding_is_count_preserving():
    rng = random.Random(20260104)
    failures = []
    for _ in range(250):
        cnf = random_cnf(rng, n_max=5)
        eqs = random_xors(rng, cnf.n)
        truth = brute_mixed(cnf, eqs)
        encoded, _ = encode_xor_equations(cnf, eqs)
        if encoded.n <= 14 and brute_cnf(encoded) != truth:
            failures.append(('encode', _fmt(cnf, eqs), brute_cnf(encoded), truth))
        got = int(count_via_xor_encoding(cnf, eqs)['count'])
        if got != truth:
            failures.append(('count_via_xor_encoding', _fmt(cnf, eqs), got, truth))
    _report('XOR Tseitin encoding', failures)


def test_empty_xor_equation_zero_equals_one_is_unsatisfiable():
    cnf = CNF.from_lists(2, [[1, 2]])
    eqs = (XorEquation((), 1),)
    assert int(count_via_xor_encoding(cnf, eqs)['count']) == 0
    encoded, _ = encode_xor_equations(cnf, eqs)
    assert brute_cnf(encoded) == 0
    # ``0 = 0`` imposes nothing.
    assert int(count_via_xor_encoding(cnf, (XorEquation((), 0),))['count']) == 3


# --------------------------------------------------------------- substitution routes
def test_substitution_and_unary_folding_preserve_mixed_count():
    rng = random.Random(20260105)
    failures = []
    for _ in range(600):
        cnf = random_cnf(rng, n_max=6)
        eqs = random_xors(rng, cnf.n)
        truth = brute_mixed(cnf, eqs)
        for label, fn in (
            ('substitute_binary_xor', lambda: substitute_binary_xor(cnf, eqs)),
            ('substitute(any pivot)', lambda: substitute_binary_xor(cnf, eqs, require_pivot_in_clauses=False)),
            ('apply_xor_unary_units', lambda: apply_xor_unary_units(cnf, eqs)),
        ):
            reduced, eqs2, info = fn()
            got = 0 if info.get('empty_clause') else brute_mixed(reduced, eqs2)
            if got != truth:
                failures.append((label, _fmt(cnf, eqs), got, truth))
    _report('XOR substitution', failures)


def test_algebraic_reduce_and_mixed_conditioning_match_brute_force():
    rng = random.Random(20260106)
    failures = []
    for _ in range(400):
        cnf = random_cnf(rng, n_max=6)
        eqs = random_xors(rng, cnf.n)
        truth = brute_mixed(cnf, eqs)
        out = try_xor_algebraic_reduce(cnf, eqs)
        if out is not None and int(out['count']) != truth:
            failures.append(('try_xor_algebraic_reduce', _fmt(cnf, eqs), int(out['count']), truth))
        if True:
            mixed = int(count_mixed_xor_cnf(cnf, eqs)['count'])
            if mixed != truth:
                failures.append(('count_mixed_xor_cnf', _fmt(cnf, eqs), mixed, truth))
    _report('algebraic reduce / mixed', failures)


# --------------------------------------------------------------------- full pipeline
def test_pipeline_matches_brute_force_with_and_without_preprocess():
    rng = random.Random(20260107)
    failures = []
    for _ in range(500):
        cnf = random_cnf(rng, n_max=6)
        eqs = random_xors(rng, cnf.n)
        truth = brute_mixed(cnf, eqs)
        for pre in (False, True):
            for verify in (True, False):
                try:
                    got = int(
                        structure_with_optional_xor(
                            cnf, xor_equations=eqs or None, preprocess=pre, verify_direct=verify
                        )['count']
                    )
                except Exception as exc:  # noqa: BLE001 - any crash is a failure here
                    got = f'{type(exc).__name__}: {exc}'
                if got != truth:
                    failures.append((f'preprocess={pre} verify={verify}', _fmt(cnf, eqs), got, truth))
    _report('structure_with_optional_xor', failures)


# ----------------------------------------------------- pinned regressions from the audit
def test_regression_explicit_empty_clause_with_preprocess():
    cnf = CNF.from_lists(2, [[1, 2], []])
    _, report = count_preserving_preprocess(cnf)
    assert report.empty_clause
    assert int(structure_aware_count(cnf, preprocess=True, timeout_s=5)['count']) == 0


def test_regression_preprocess_renumbering_must_remap_xor_ids():
    cnf = CNF.from_lists(6, [[-1], [-2, 2], [5, -6]])
    eqs = (XorEquation((1,), 1), XorEquation((2, 3), 1), XorEquation((5, 1), 1))
    assert brute_mixed(cnf, eqs) == 0  # x1 must be 0 (clause) and 1 (xor)
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=True, verify_direct=False)
    assert int(out['count']) == 0


def test_regression_substitution_must_propagate_to_other_xor_equations():
    cnf = CNF.from_lists(4, [[-2, 4, 3], [3]])
    eqs = (XorEquation((2, 4), 1), XorEquation((2, 3, 4), 0))
    assert brute_mixed(cnf, eqs) == 4
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, verify_direct=False)
    assert int(out['count']) == 4


def test_regression_unary_xor_unit_has_correct_polarity():
    # x1 = 1 satisfies the literal x1 and falsifies -x1, so [-1, 2] forces x2 = 1.
    cnf = CNF.from_lists(2, [[-1, 2]])
    eqs = (XorEquation((1,), 1),)
    assert brute_mixed(cnf, eqs) == 1
    reduced, eqs2, info = apply_xor_unary_units(cnf, eqs)
    assert not info.get('empty_clause')
    assert brute_mixed(reduced, eqs2) == 1
    assert int(structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False)['count']) == 1

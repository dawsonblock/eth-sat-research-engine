"""Guards for the performance and CLI-honesty changes: outputs must not change."""
import contextlib
import io
import random
import unittest
from itertools import combinations
from unittest import mock

from eth_sat import references
from eth_sat.cli import main
from eth_sat.model import CNF
from eth_sat.references import _exhaustive_count_python, dpll_count, exhaustive_count
from eth_sat.reductions import normalize_clause_family

try:
    import numpy  # noqa: F401
except ImportError:  # pragma: no cover - exercised only without NumPy
    numpy = None


def _random_formula(rng, n, *, max_clauses=9, allow_empty=True):
    lengths = [0, 1, 2, 3, 3, 4] if allow_empty else [1, 2, 3, 3, 4]
    if n == 0:
        lengths = [0]  # no variables to draw literals from
    clauses = [
        tuple((1 if rng.randrange(2) else -1) * rng.randint(1, n)
              for _ in range(rng.choice(lengths)))
        for _ in range(rng.randint(0, max_clauses))
    ]
    return CNF.from_signed_clauses(n, clauses)


def _reference_normalize(clauses):
    """The previous list-scan implementation, kept verbatim as the oracle."""
    normalized = set()
    for source in clauses:
        clause = frozenset(source)
        if any(-literal in clause for literal in clause):
            continue
        normalized.add(clause)
    if frozenset() in normalized:
        return ((),)
    kept = []
    for clause in sorted(normalized, key=lambda item: (len(item), tuple(sorted(item)))):
        ordered = tuple(sorted(clause))
        if not any(frozenset(sub) in kept for size in range(len(ordered))
                   for sub in combinations(ordered, size)):
            kept.append(clause)
    return tuple(tuple(sorted(clause)) for clause in kept)


@unittest.skipIf(numpy is None, "NumPy not installed")
class ExhaustiveFastPathTests(unittest.TestCase):
    def test_numpy_matches_python_including_empty_clauses(self):
        rng = random.Random(20261114)
        for _ in range(120):
            formula = _random_formula(rng, rng.randint(0, 13))
            with mock.patch.object(references, "_NUMPY_MIN_VARIABLES", 0):
                fast = exhaustive_count(formula)
            self.assertEqual(fast, _exhaustive_count_python(formula), formula)

    def test_high_bit_blocks_match_python(self):
        # Force several vectorised blocks so the looped high-bit path is exercised.
        rng = random.Random(7)
        for _ in range(40):
            formula = _random_formula(rng, rng.randint(6, 13))
            with mock.patch.object(references, "_NUMPY_MIN_VARIABLES", 0), \
                    mock.patch.object(references, "_NUMPY_LOW_BITS", 3):
                fast = exhaustive_count(formula)
            self.assertEqual(fast, _exhaustive_count_python(formula), formula)

    def test_default_path_agrees_with_dpll_above_threshold(self):
        rng = random.Random(99)
        for _ in range(6):
            formula = _random_formula(rng, rng.randint(13, 16), allow_empty=False)
            self.assertEqual(exhaustive_count(formula), dpll_count(formula))


class NormalizeTests(unittest.TestCase):
    def test_matches_previous_implementation(self):
        rng = random.Random(31337)
        for _ in range(300):
            n = rng.randint(1, 6)
            clauses = [
                tuple((1 if rng.randrange(2) else -1) * rng.randint(1, n)
                      for _ in range(rng.randint(0, 4)))
                for _ in range(rng.randint(0, 14))
            ]
            self.assertEqual(normalize_clause_family(clauses), _reference_normalize(clauses))


class CliAndParserHonestyTests(unittest.TestCase):
    def _run(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()

    def test_fallback_is_labelled_as_a_truth_table(self):
        code, text = self._run("--example", "simple", "--engine", "subexponential")
        self.assertEqual(code, 0)
        self.assertIn("finite-size fallback", text)
        self.assertNotIn("Sparsification", text)

    def test_columns_stay_aligned_for_long_labels(self):
        _, text = self._run("--example", "simple", "--engine", "subexponential")
        header, row = text.splitlines()[1:3]
        self.assertEqual(header.index("Exact"), row.rindex(row.split()[-1]))

    def test_mistyped_path_is_reported_as_such(self):
        with self.assertRaisesRegex(ValueError, "neither an existing file nor DIMACS"):
            CNF.from_dimacs("no_such_file_here.cnf")
        self.assertEqual(CNF.from_dimacs("p cnf 2 0").num_variables, 2)


if __name__ == "__main__":
    unittest.main()

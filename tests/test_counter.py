"""Tests for the ``sat-count`` tool.

The oracle below enumerates assignments directly and shares no code with any
engine, so an error common to the engines cannot hide behind their agreement.
"""

from __future__ import annotations

import io
import random
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from itertools import product
from pathlib import Path
from unittest import mock

from eth_sat import counter
from eth_sat.counter import (
    DimacsError,
    EngineRun,
    Problem,
    count_bitset,
    count_dpll,
    count_models,
    encode_xors,
    parse_dimacs,
    plan_engines,
)

HAVE_GANAK = counter.engine_availability()["ganak"] is None
HAVE_VERITAS = counter.engine_availability()["veritas"] is None


def oracle(problem: Problem) -> int:
    kept = (
        range(problem.num_variables)
        if problem.projection is None
        else [v - 1 for v in problem.projection]
    )
    seen = set()
    for bits in product((False, True), repeat=problem.num_variables):
        if not all(any(bits[abs(l) - 1] == (l > 0) for l in clause) for clause in problem.clauses):
            continue
        if not all(sum(bits[v - 1] for v in vs) % 2 == rhs for vs, rhs in problem.xors):
            continue
        seen.add(tuple(bits[i] for i in kept))
    return len(seen)


def random_problem(rng: random.Random, *, xors: bool, projection: bool) -> Problem:
    n = rng.randint(1, 9)
    clauses = []
    for _ in range(rng.randint(0, 2 * n)):
        width = rng.randint(1, min(4, n))
        clauses.append(
            tuple(v if rng.random() < 0.5 else -v for v in rng.sample(range(1, n + 1), width))
        )
    equations = []
    if xors:
        for _ in range(rng.randint(0, 3)):
            size = rng.randint(0, n)
            equations.append((tuple(sorted(rng.sample(range(1, n + 1), size))), rng.randint(0, 1)))
    kept = None
    if projection:
        kept = tuple(sorted(rng.sample(range(1, n + 1), rng.randint(0, n))))
    return Problem(n, tuple(clauses), tuple(equations), kept)


class ParseTests(unittest.TestCase):
    def test_clauses_xors_projection_and_normalization(self) -> None:
        problem = parse_dimacs(
            "c comment\n"
            "c p show 3 1 0\n"
            "p cnf 4 5\n"
            "1 -2\n 3 0 2 2 0\n"
            "1 -1 4 0\n"
            "x1 -2 3 0\n"
            "x 2 2 4 0\n"
        )
        self.assertEqual(problem.num_variables, 4)
        self.assertEqual(problem.clauses, ((1, -2, 3), (2,)))
        self.assertEqual(problem.xors, (((1, 2, 3), 0), ((4,), 1)))
        self.assertEqual(problem.projection, (1, 3))
        self.assertEqual(problem.warnings, ())

    def test_ind_projection_and_end_marker(self) -> None:
        problem = parse_dimacs("c ind 2 0\np cnf 2 1\n1 2 0\n%\n0\n")
        self.assertEqual(problem.projection, (2,))
        self.assertEqual(problem.clauses, ((1, 2),))

    def test_clause_count_mismatch_is_a_warning(self) -> None:
        self.assertTrue(parse_dimacs("p cnf 2 5\n1 0\n").warnings)

    def test_rejects_bad_input(self) -> None:
        for text in (
            "1 2 0\n",
            "p cnf 2 1\n1 3 0\n",
            "p cnf 2 1\n1 2\n",
            "p cnf 2 1\nc p weight 1 0.5 0\n1 0\n",
            "p wcnf 2 1\n1 0\n",
            "p cnf 2 1\n1 a 0\n",
            "p cnf 2 1\nx1 2\n",
            "c p show 3 0\np cnf 2 1\n1 0\n",
            "",
        ):
            with self.subTest(text=text):
                with self.assertRaises(DimacsError):
                    parse_dimacs(text)


class EngineTests(unittest.TestCase):
    def test_small_known_counts(self) -> None:
        self.assertEqual(count_bitset(Problem(0, ())), 1)
        self.assertEqual(count_bitset(Problem(5, ((1,),))), 16)
        self.assertEqual(count_bitset(Problem(3, ((),))), 0)
        self.assertEqual(count_bitset(Problem(2, ((1, 2),), (), (1,))), 2)
        self.assertEqual(count_bitset(Problem(2, (), (((), 1),))), 0)
        self.assertEqual(count_dpll(Problem(5, ((1,),))), 16)
        self.assertEqual(count_dpll(Problem(3, ((),))), 0)

    def test_bitset_matches_oracle_with_xors_and_projection(self) -> None:
        rng = random.Random(1)
        for _ in range(400):
            problem = random_problem(rng, xors=True, projection=rng.random() < 0.5)
            self.assertEqual(count_bitset(problem), oracle(problem), problem)

    def test_dpll_matches_oracle_with_xors(self) -> None:
        rng = random.Random(2)
        for _ in range(250):
            problem = random_problem(rng, xors=True, projection=False)
            self.assertEqual(count_dpll(problem), oracle(problem), problem)

    @unittest.skipUnless(HAVE_GANAK, "pyganak not installed")
    def test_ganak_matches_oracle_with_xors_and_projection(self) -> None:
        rng = random.Random(3)
        for _ in range(250):
            problem = random_problem(rng, xors=True, projection=rng.random() < 0.5)
            self.assertEqual(counter.count_ganak(problem), oracle(problem), problem)

    @unittest.skipUnless(HAVE_VERITAS, "veritas package not importable")
    def test_veritas_matches_oracle_with_xors(self) -> None:
        rng = random.Random(4)
        for _ in range(150):
            problem = random_problem(rng, xors=True, projection=False)
            self.assertEqual(counter.count_veritas(problem), oracle(problem), problem)

    def test_xor_encoding_preserves_the_count(self) -> None:
        rng = random.Random(5)
        for _ in range(60):
            n = rng.randint(4, 9)
            variables = tuple(sorted(rng.sample(range(1, n + 1), rng.randint(4, n))))
            problem = Problem(n, ((1, -2),), ((variables, rng.randint(0, 1)),))
            clauses, total = encode_xors(problem)
            self.assertGreater(total, n)
            self.assertEqual(count_bitset(Problem(total, tuple(clauses))), count_bitset(problem))

    def test_xor_encoding_keeps_an_empty_contradiction(self) -> None:
        clauses, total = encode_xors(Problem(0, (), (((), 1),)))
        self.assertEqual((clauses, total), ([()], 0))
        self.assertEqual(count_bitset(Problem(total, tuple(clauses))), 0)
        clauses, total = encode_xors(Problem(2, ((1, 2),), (((), 0),)))
        self.assertEqual((clauses, total), ([(1, 2)], 2))

    def test_bitset_refuses_large_inputs(self) -> None:
        with self.assertRaises(counter.EngineSkipped):
            count_bitset(Problem(counter.BITSET_MAX_VARIABLES + 1, ()))


class OrchestrationTests(unittest.TestCase):
    chain = Problem(13, tuple((i, i + 1) for i in range(1, 13)))

    def test_plan(self) -> None:
        self.assertIn("bitset", plan_engines(self.chain))
        self.assertNotIn("dpll", plan_engines(Problem(3, (), (), (1,))))
        self.assertNotIn("bitset", plan_engines(Problem(40, ())))
        self.assertEqual(plan_engines(self.chain, "bitset, dpll,bitset"), ["bitset", "dpll"])
        with self.assertRaises(ValueError):
            plan_engines(self.chain, "nope")

    def test_discovery_requires_the_module_an_engine_uses(self) -> None:
        with mock.patch.dict(counter._REQUIRED_MODULES, {"veritas": "json.no_such_module"}):
            self.assertIsNotNone(counter.engine_availability()["veritas"])
            self.assertNotIn("veritas", plan_engines(self.chain))
        with mock.patch.dict(counter._REQUIRED_MODULES, {"veritas": "no_such_package.sub"}):
            self.assertIsNotNone(counter.engine_availability()["veritas"])
        with mock.patch.dict(counter._REQUIRED_MODULES, {"veritas": "json.decoder"}):
            self.assertIsNone(counter.engine_availability()["veritas"])

    def test_isolated_engines_agree(self) -> None:
        result = count_models(self.chain, engines="dpll,bitset", timeout=30, verify_timeout=30)
        self.assertEqual((result.status, result.count), ("EXACT", "610"))
        self.assertEqual(result.agreeing_engines, ("dpll", "bitset"))
        self.assertTrue(result.cross_checked)
        self.assertFalse(result.to_json()["subexponential_claim"])

    def test_timeout_is_not_a_count(self) -> None:
        rng = random.Random(6)
        n = 250
        clauses = tuple(
            tuple(v if rng.random() < 0.5 else -v for v in rng.sample(range(1, n + 1), 3))
            for _ in range(1065)
        )
        result = count_models(Problem(n, clauses), engines="dpll", timeout=0.5)
        self.assertEqual((result.status, result.count), ("NO_RESULT", None))
        self.assertEqual(result.runs[0].status, "timeout")

    def test_disagreement_publishes_no_count(self) -> None:
        fake = iter([EngineRun("dpll", "ok", "5", 0.0), EngineRun("bitset", "ok", "6", 0.0)])
        with mock.patch.object(counter, "run_engine", lambda *a, **k: next(fake)):
            result = count_models(self.chain, engines="dpll,bitset")
        self.assertEqual((result.status, result.count, result.agreeing_engines), ("DISAGREE", None, ()))

    def test_failed_primary_falls_back_to_the_next_engine(self) -> None:
        result = count_models(Problem(3, (), (), (1,)), engines="dpll,bitset", isolate=False)
        self.assertEqual([run.status for run in result.runs], ["skipped", "ok"])
        self.assertEqual((result.status, result.count), ("EXACT", "2"))
        self.assertFalse(result.cross_checked)

    def test_counts_beyond_the_integer_string_limit(self) -> None:
        # 2**15000 has 4516 decimal digits, above Python's default conversion limit.
        expected = counter.to_decimal(2**15000)
        self.assertGreater(len(expected), 4300)
        problem = Problem(15000, ())
        for isolate in (False, True):
            result = count_models(problem, engines="dpll", isolate=isolate)
            self.assertEqual((result.status, result.count), ("EXACT", expected))
        self.assertEqual(counter.from_decimal(expected), 2**15000)

    @unittest.skipUnless(HAVE_GANAK, "pyganak not installed")
    def test_ganak_counts_beyond_the_integer_string_limit(self) -> None:
        problem = Problem(15000, ((1, 2),))
        result = count_models(problem, engines="ganak,dpll", isolate=False)
        self.assertEqual(result.agreeing_engines, ("ganak", "dpll"))
        self.assertEqual(result.count, counter.to_decimal(3 * 2**14998))

    def test_engine_error_is_reported_not_counted(self) -> None:
        with mock.patch.dict(counter.ENGINES, {"bitset": lambda problem: 1 / 0}):
            result = count_models(self.chain, engines="bitset", isolate=False)
        self.assertEqual(result.status, "NO_RESULT")
        self.assertEqual(result.runs[0].status, "error")


class CliTests(unittest.TestCase):
    def run_cli(self, text: str, *args: str) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "f.cnf"
            path.write_text(text)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = counter.main([str(path), *args])
        return code, out.getvalue(), err.getvalue()

    def test_prints_only_the_count_on_stdout(self) -> None:
        code, out, err = self.run_cli("p cnf 3 2\n1 2 0\n-1 3 0\n", "--engines", "dpll,bitset")
        self.assertEqual((code, out), (0, "4\n"))
        self.assertIn("cross-checked by 2 engines", err)

    def test_exit_codes(self) -> None:
        text = "p cnf 3 1\n1 2 0\n"
        self.assertEqual(self.run_cli("p cnf 1 1\n2 0\n")[0], counter.EXIT_BAD_INPUT)
        self.assertEqual(self.run_cli(text, "--engines", "nope")[0], counter.EXIT_BAD_INPUT)
        code, out, _ = self.run_cli(text, "--engines", "bitset", "--require-cross-check")
        self.assertEqual((code, out), (counter.EXIT_NOT_CROSS_CHECKED, "6\n"))
        fake = iter([EngineRun("dpll", "ok", "5", 0.0), EngineRun("bitset", "ok", "6", 0.0)])
        with mock.patch.object(counter, "run_engine", lambda *a, **k: next(fake)):
            code, out, err = self.run_cli(text, "--engines", "dpll,bitset")
        self.assertEqual((code, out), (counter.EXIT_DISAGREE, ""))
        self.assertIn("DISAGREE", err)

    def test_prints_a_count_beyond_the_integer_string_limit(self) -> None:
        code, out, _ = self.run_cli("p cnf 15000 0\n", "--engines", "dpll")
        self.assertEqual((code, out.strip()), (0, counter.to_decimal(2**15000)))
        code, out, _ = self.run_cli("p cnf 15000 0\n", "--engines", "dpll", "--json")
        self.assertEqual(code, 0)
        self.assertIn(counter.to_decimal(2**15000), out)

    def test_reports_when_no_engine_applies(self) -> None:
        text = "c p show 1 2 0\np cnf 30 1\n1 2 0\n"
        with mock.patch.dict(counter._REQUIRED_MODULES, {"ganak": "json.no_such_module"}):
            code, out, err = self.run_cli(text)
        self.assertEqual((code, out), (counter.EXIT_NO_RESULT, ""))
        self.assertIn("no engine applies", err)

    def test_json_record(self) -> None:
        code, out, _ = self.run_cli("p cnf 2 1\nx1 2 0\n", "--engines", "bitset", "--json")
        self.assertEqual(code, 0)
        self.assertIn('"count": "2"', out)
        self.assertIn('"num_xors": 1', out)


if __name__ == "__main__":
    unittest.main()

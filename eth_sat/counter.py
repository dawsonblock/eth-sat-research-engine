"""Practical exact model counting with independent cross-checks.

``sat-count formula.cnf`` prints the exact number of satisfying assignments of
a DIMACS CNF. It runs a fast counter (Ganak, when the optional ``pyganak``
package is installed) and then re-counts with independent engines where they
can finish. A count is published only when every engine that finished agrees.

This is ordinary exponential-worst-case model counting. It makes no use of,
and is no evidence for, any subexponential algorithm.

Supported input: DIMACS CNF, CryptoMiniSat-style XOR lines (``x1 -2 3 0``) and
projection sets (``c p show 1 2 0`` or ``c ind 1 2 0``). Weighted counting is
refused.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import monotonic

BITSET_MAX_VARIABLES = 24
VERITAS_MAX_VARIABLES = 512
VERITAS_MAX_CLAUSES = 20_000

EXIT_EXACT = 0
EXIT_NO_RESULT = 2
EXIT_DISAGREE = 3
EXIT_NOT_CROSS_CHECKED = 4
EXIT_BAD_INPUT = 64


class DimacsError(ValueError):
    """The input is not a counting problem this tool accepts."""


class EngineSkipped(Exception):
    """The engine does not apply to this problem."""


class EngineUnavailable(Exception):
    """The engine's package is not installed."""


@dataclass(frozen=True)
class Problem:
    """A CNF with optional XOR constraints and an optional projection set.

    ``xors`` holds ``(variables, rhs)``: the XOR of the listed variables equals
    ``rhs``. ``projection`` of ``None`` counts over every declared variable.
    """

    num_variables: int
    clauses: tuple[tuple[int, ...], ...]
    xors: tuple[tuple[tuple[int, ...], int], ...] = ()
    projection: tuple[int, ...] | None = None
    warnings: tuple[str, ...] = ()


# --------------------------------------------------------------------- parsing
def _clause(literals: list[int]) -> tuple[int, ...] | None:
    """Deduplicate literals; ``None`` for a tautology."""
    seen = set(literals)
    if any(-literal in seen for literal in seen):
        return None
    return tuple(sorted(seen, key=lambda literal: (abs(literal), literal)))


def _xor(literals: list[int]) -> tuple[tuple[int, ...], int]:
    """``l1 xor l2 xor ... = true`` as (variables, rhs); repeated variables cancel."""
    rhs = 1
    odd: set[int] = set()
    for literal in literals:
        if literal < 0:
            rhs ^= 1
        odd ^= {abs(literal)}
    return tuple(sorted(odd)), rhs


def parse_dimacs(text: str) -> Problem:
    num_variables: int | None = None
    declared_clauses = 0
    clauses: list[tuple[int, ...]] = []
    xors: list[tuple[tuple[int, ...], int]] = []
    projection: list[int] | None = None
    pending: list[int] = []
    constraints = 0

    def ints(tokens: list[str], line_number: int) -> list[int]:
        try:
            return [int(token) for token in tokens]
        except ValueError:
            raise DimacsError(f"line {line_number}: expected integers") from None

    def check(values: list[int], line_number: int) -> None:
        if num_variables is None:
            raise DimacsError(f"line {line_number}: constraint before the 'p cnf' header")
        for value in values:
            if abs(value) > num_variables:
                raise DimacsError(
                    f"line {line_number}: variable {abs(value)} exceeds the declared {num_variables}"
                )

    for line_number, raw in enumerate(text.splitlines(), 1):
        tokens = raw.split()
        if not tokens:
            continue
        head = tokens[0]
        if head == "%":
            break
        if head == "c":
            if tokens[1:3] == ["p", "show"] or tokens[1:2] == ["ind"]:
                values = ints(tokens[3:] if tokens[1] == "p" else tokens[2:], line_number)
                projection = (projection or []) + [value for value in values if value != 0]
            elif tokens[1:3] == ["p", "weight"] or tokens[1:3] in (["t", "wmc"], ["t", "pwmc"]):
                raise DimacsError(f"line {line_number}: weighted counting is not supported")
            continue
        if head == "p":
            if num_variables is not None:
                raise DimacsError(f"line {line_number}: second problem header")
            if len(tokens) != 4 or tokens[1] != "cnf":
                raise DimacsError(f"line {line_number}: expected 'p cnf <variables> <clauses>'")
            num_variables, declared_clauses = ints(tokens[2:], line_number)
            if num_variables < 0 or declared_clauses < 0:
                raise DimacsError(f"line {line_number}: negative size in header")
            continue
        if head.startswith("x"):
            if pending:
                raise DimacsError(f"line {line_number}: XOR line inside an unfinished clause")
            values = ints(([head[1:]] if head[1:] else []) + tokens[1:], line_number)
            if not values or values[-1] != 0 or 0 in values[:-1]:
                raise DimacsError(f"line {line_number}: an XOR line must end with a single 0")
            check(values, line_number)
            xors.append(_xor(values[:-1]))
            constraints += 1
            continue
        values = ints(tokens, line_number)
        check(values, line_number)
        for value in values:
            if value == 0:
                normalized = _clause(pending)
                if normalized is not None:
                    clauses.append(normalized)
                pending = []
                constraints += 1
            else:
                pending.append(value)

    if num_variables is None:
        raise DimacsError("no 'p cnf' header")
    if pending:
        raise DimacsError("last clause is not terminated by 0")
    warnings = []
    if constraints != declared_clauses:
        warnings.append(f"header declares {declared_clauses} clauses, file has {constraints}")
    if projection is not None:
        for variable in projection:
            if not 1 <= variable <= num_variables:
                raise DimacsError(f"projection variable {variable} is out of range")
        projection = sorted(set(projection))
    return Problem(
        num_variables,
        tuple(clauses),
        tuple(xors),
        None if projection is None else tuple(projection),
        tuple(warnings),
    )


# --------------------------------------------------------------------- engines
def _trivially_unsatisfiable(problem: Problem) -> bool:
    return any(not clause for clause in problem.clauses) or any(
        not variables and rhs for variables, rhs in problem.xors
    )


def encode_xors(problem: Problem) -> tuple[list[tuple[int, ...]], int]:
    """CNF clauses for the whole problem and the variable count including helpers.

    Each helper variable equals the XOR of two others, so every assignment of
    the original variables has exactly one extension. Counts are unchanged.
    """
    clauses = list(problem.clauses)
    total = problem.num_variables

    def emit(variables: list[int], rhs: int) -> None:
        for bits in range(1 << len(variables)):
            if bin(bits).count("1") % 2 != rhs:
                clauses.append(
                    tuple(-v if bits >> i & 1 else v for i, v in enumerate(variables))
                )

    for variables, rhs in problem.xors:
        chain = list(variables)
        while len(chain) > 3:
            total += 1
            emit([chain[0], chain[1], total], 0)
            chain = [total] + chain[2:]
        if chain:
            emit(chain, rhs)
    return clauses, total


def count_bitset(problem: Problem) -> int:
    """Truth-table counting on Python integers. Shares no code with the other engines."""
    n = problem.num_variables
    if n > BITSET_MAX_VARIABLES:
        raise EngineSkipped(f"more than {BITSET_MAX_VARIABLES} variables")
    everything = (1 << (1 << n)) - 1
    # tables[v] has bit a set exactly when variable v is true in assignment a.
    tables = [0] + [
        (everything // ((1 << (1 << i)) + 1)) << (1 << i) for i in range(n)
    ]
    satisfied = everything
    for clause in problem.clauses:
        any_literal = 0
        for literal in clause:
            table = tables[abs(literal)]
            any_literal |= table if literal > 0 else everything ^ table
        satisfied &= any_literal
    for variables, rhs in problem.xors:
        parity = 0
        for variable in variables:
            parity ^= tables[variable]
        satisfied &= parity if rhs else everything ^ parity
    if problem.projection is not None:
        kept = set(problem.projection)
        for variable in range(1, n + 1):
            if variable not in kept:
                shift = 1 << (variable - 1)
                satisfied = (satisfied | (satisfied >> shift)) & (everything ^ tables[variable])
    return satisfied.bit_count()


def count_ganak(problem: Problem) -> int:
    try:
        import pyganak
    except ImportError:
        raise EngineUnavailable("pyganak is not installed (pip install pyganak)") from None
    if _trivially_unsatisfiable(problem):
        return 0
    clauses, total = encode_xors(problem)
    counter = pyganak.Counter()
    counter.new_vars(total)
    for clause in clauses:
        counter.add_clause(list(clause))
    if problem.projection is not None:
        counter.set_sampling_set(list(problem.projection))
    return int(counter.count())


def count_dpll(problem: Problem) -> int:
    if problem.projection is not None:
        raise EngineSkipped("no projection support")
    if _trivially_unsatisfiable(problem):
        return 0
    from .model import CNF
    from .references import dpll_count

    clauses, total = encode_xors(problem)
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 20 * total + 1000))
    return dpll_count(CNF.from_signed_clauses(total, clauses))


def count_veritas(problem: Problem) -> int:
    """The R9.12 structure-aware counter, when the ``veritas`` package is importable."""
    if problem.projection is not None:
        raise EngineSkipped("no projection support")
    if (
        problem.num_variables > VERITAS_MAX_VARIABLES
        or len(problem.clauses) > VERITAS_MAX_CLAUSES
    ):
        raise EngineSkipped("outside the engine's input caps")
    try:
        from veritas.core.cnf import CNF
        from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
    except ImportError:
        raise EngineUnavailable("the veritas package is not importable") from None
    if _trivially_unsatisfiable(problem):
        return 0
    if problem.num_variables == 0:
        raise EngineSkipped("no variables")
    equations = tuple(XorEquation(variables, rhs) for variables, rhs in problem.xors if variables)
    result = structure_with_optional_xor(
        CNF.from_lists(problem.num_variables, [list(clause) for clause in problem.clauses]),
        xor_equations=equations or None,
        preprocess=True,
        portfolio_mode="auto",
    )
    if result.get("status") != "EXACT_COUNT":
        raise RuntimeError(f"no exact count: {result.get('status')}")
    return int(result["count"])


ENGINES = {
    "ganak": count_ganak,
    "dpll": count_dpll,
    "bitset": count_bitset,
    "veritas": count_veritas,
}
_PACKAGES = {"ganak": "pyganak", "veritas": "veritas"}


def engine_availability() -> dict[str, str | None]:
    """Engine name to ``None`` when usable, otherwise the reason it is not."""
    status: dict[str, str | None] = {}
    for name in ENGINES:
        package = _PACKAGES.get(name)
        missing = package is not None and importlib.util.find_spec(package) is None
        status[name] = f"{package} is not installed" if missing else None
    return status


def plan_engines(problem: Problem, engines: str | list[str] = "auto") -> list[str]:
    """Engines to run, primary first."""
    if engines != "auto":
        names = engines.split(",") if isinstance(engines, str) else list(engines)
        names = [name.strip() for name in names if name.strip()]
        unknown = [name for name in names if name not in ENGINES]
        if unknown or not names:
            raise ValueError(f"unknown engine: {', '.join(unknown) or '(none)'}")
        return list(dict.fromkeys(names))
    available = engine_availability()
    chosen = []
    if available["ganak"] is None:
        chosen.append("ganak")
    if problem.num_variables <= BITSET_MAX_VARIABLES:
        chosen.append("bitset")
    if (
        available["veritas"] is None
        and problem.projection is None
        and 0 < problem.num_variables <= VERITAS_MAX_VARIABLES
        and len(problem.clauses) <= VERITAS_MAX_CLAUSES
    ):
        chosen.append("veritas")
    # Last: the pure-Python DPLL is the engine most likely to hit its time limit.
    if problem.projection is None:
        chosen.append("dpll")
    return chosen


# ----------------------------------------------------------------- orchestration
@dataclass(frozen=True)
class EngineRun:
    engine: str
    status: str  # ok | timeout | skipped | unavailable | error
    count: str | None
    seconds: float
    detail: str = ""


@dataclass(frozen=True)
class CountResult:
    status: str  # EXACT | DISAGREE | NO_RESULT
    count: str | None
    agreeing_engines: tuple[str, ...]
    runs: tuple[EngineRun, ...]
    num_variables: int
    num_clauses: int
    num_xors: int
    projection_size: int | None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def cross_checked(self) -> bool:
        return self.status == "EXACT" and len(self.agreeing_engines) >= 2

    def to_json(self) -> dict:
        data = asdict(self)
        data["cross_checked"] = self.cross_checked
        data["subexponential_claim"] = False
        return data


def _execute(name: str, problem: Problem) -> tuple[str, str]:
    try:
        return "ok", str(ENGINES[name](problem))
    except EngineSkipped as exc:
        return "skipped", str(exc)
    except EngineUnavailable as exc:
        return "unavailable", str(exc)
    except (MemoryError, RecursionError) as exc:
        return "error", type(exc).__name__
    except Exception as exc:  # an engine failure must never look like a count
        return "error", f"{type(exc).__name__}: {exc}"


_RESULT_MARK = "@@sat-count-result@@"
_WORKER = "from eth_sat.counter import _worker_main; _worker_main()"


def _worker_main() -> None:
    """Child-process entry: problem as JSON on stdin, one marked result line on stdout."""
    data = json.load(sys.stdin)
    problem = Problem(
        data["num_variables"],
        tuple(tuple(clause) for clause in data["clauses"]),
        tuple((tuple(variables), rhs) for variables, rhs in data["xors"]),
        None if data["projection"] is None else tuple(data["projection"]),
    )
    result = _execute(sys.argv[1], problem)
    sys.stdout.write("\n" + _RESULT_MARK + json.dumps(result) + "\n")
    sys.stdout.flush()


def _run_isolated(name: str, problem: Problem, timeout: float) -> tuple[str, str]:
    payload = json.dumps(
        {
            "num_variables": problem.num_variables,
            "clauses": problem.clauses,
            "xors": problem.xors,
            "projection": problem.projection,
        }
    )
    # The child must import this package however the parent found it.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(entry or os.getcwd() for entry in sys.path)
    try:
        done = subprocess.run(
            [sys.executable, "-c", _WORKER, name],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return "timeout", f"no result within {timeout:g}s"
    marked = [line for line in done.stdout.splitlines() if line.startswith(_RESULT_MARK)]
    if not marked:
        return "error", f"engine process exited with code {done.returncode} and no result"
    status, detail = json.loads(marked[-1][len(_RESULT_MARK):])
    return status, detail


def run_engine(name: str, problem: Problem, timeout: float, *, isolate: bool = True) -> EngineRun:
    """Run one engine, in its own process with a hard wall-clock limit when isolated."""
    started = monotonic()
    if not isolate:
        status, payload = _execute(name, problem)
    else:
        status, payload = _run_isolated(name, problem, timeout)
    seconds = round(monotonic() - started, 3)
    if status == "ok":
        return EngineRun(name, "ok", payload, seconds)
    return EngineRun(name, status, None, seconds, payload)


def count_models(
    problem: Problem,
    *,
    engines: str | list[str] = "auto",
    timeout: float = 60.0,
    verify_timeout: float = 10.0,
    verify: bool = True,
    isolate: bool = True,
) -> CountResult:
    """Count models with the first planned engine and re-count with the others."""
    if timeout <= 0 or verify_timeout <= 0:
        raise ValueError("timeouts must be positive")
    names = plan_engines(problem, engines)
    if not verify:
        names = names[:1]
    runs = []
    for index, name in enumerate(names):
        have_count = any(run.status == "ok" for run in runs)
        budget = verify_timeout if index and have_count else timeout
        runs.append(run_engine(name, problem, budget, isolate=isolate))
    finished = [run for run in runs if run.status == "ok"]
    counts = {run.count for run in finished}
    if not finished:
        status, count, agreeing = "NO_RESULT", None, ()
    elif len(counts) == 1:
        status, count = "EXACT", finished[0].count
        agreeing = tuple(run.engine for run in finished)
    else:
        status, count, agreeing = "DISAGREE", None, ()
    return CountResult(
        status,
        count,
        agreeing,
        tuple(runs),
        problem.num_variables,
        len(problem.clauses),
        len(problem.xors),
        None if problem.projection is None else len(problem.projection),
        problem.warnings,
    )


# --------------------------------------------------------------------------- CLI
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sat-count",
        description="Exact model count of a DIMACS CNF, cross-checked by independent engines.",
        epilog="Exit codes: 0 exact count, 2 no engine finished, 3 engines disagree, "
        "4 not cross-checked (with --require-cross-check), 64 bad input.",
    )
    parser.add_argument("input", nargs="?", help="DIMACS file, or - for standard input")
    parser.add_argument(
        "--engines",
        default="auto",
        help=f"comma-separated subset of {','.join(ENGINES)}; the first is the primary",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="seconds for the primary engine")
    parser.add_argument(
        "--verify-timeout", type=float, default=10.0, help="seconds for each cross-check"
    )
    parser.add_argument("--no-verify", action="store_true", help="run the primary engine only")
    parser.add_argument(
        "--require-cross-check",
        action="store_true",
        help="fail unless at least two engines finished and agree",
    )
    parser.add_argument("--json", action="store_true", help="print the full record as JSON")
    parser.add_argument("--quiet", action="store_true", help="print nothing but the count")
    parser.add_argument("--list-engines", action="store_true", help="show engines and exit")
    return parser


def _summary(result: CountResult) -> str:
    parts = []
    for run in result.runs:
        note = f"{run.seconds:g}s" if run.status == "ok" else f"{run.status}: {run.detail}"
        parts.append(f"{run.engine} {note}")
    if result.status == "EXACT":
        agreed = len(result.agreeing_engines)
        head = (
            f"exact, cross-checked by {agreed} engines"
            if agreed >= 2
            else "exact, single engine only (not cross-checked)"
        )
    elif result.status == "DISAGREE":
        head = "ENGINES DISAGREE, no count published: " + ", ".join(
            f"{run.engine}={run.count}" for run in result.runs if run.status == "ok"
        )
    else:
        head = "no engine finished"
    return f"{head} [{'; '.join(parts)}]"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.list_engines:
        for name, reason in engine_availability().items():
            print(f"{name}: {'available' if reason is None else reason}")
        return EXIT_EXACT
    if args.input is None:
        parser.error("an input file is required")
    try:
        text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text()
        problem = parse_dimacs(text)
        result = count_models(
            problem,
            engines=args.engines,
            timeout=args.timeout,
            verify_timeout=args.verify_timeout,
            verify=not args.no_verify,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"sat-count: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.json:
        print(json.dumps(result.to_json(), indent=2))
    else:
        if result.count is not None:
            print(result.count)
        if not args.quiet:
            for warning in result.warnings:
                print(f"warning: {warning}", file=sys.stderr)
            print(_summary(result), file=sys.stderr)
    if result.status == "DISAGREE":
        return EXIT_DISAGREE
    if result.status != "EXACT":
        return EXIT_NO_RESULT
    if args.require_cross_check and not result.cross_checked:
        return EXIT_NOT_CROSS_CHECKED
    return EXIT_EXACT


if __name__ == "__main__":
    raise SystemExit(main())

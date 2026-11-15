"""Practical exact model counting with independent cross-checks.

``sat-count formula.cnf`` prints the exact number of satisfying assignments of
a DIMACS CNF. It runs a fast counter (Ganak, when the optional ``pyganak``
package is installed) side by side with independent engines, each in its own
process. A count is published only when every engine that finished agrees.

This is ordinary exponential-worst-case model counting. It makes no use of,
and is no evidence for, any subexponential algorithm.

Supported input: DIMACS CNF, CryptoMiniSat-style XOR lines (``x1 -2 3 0``) and
projection sets (``c p show 1 2 0`` or ``c ind 1 2 0``). Files may be gzip,
bzip2 or xz compressed. Weighted counting is refused.
"""

from __future__ import annotations

import argparse
import heapq
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import monotonic, sleep

BITSET_MAX_VARIABLES = 24
ELIMINATION_MAX_SCOPE = 18
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
def read_text(path: str | Path) -> str:
    """Read a DIMACS file, decompressing by suffix."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".gz":
        import gzip as codec
    elif suffix == ".bz2":
        import bz2 as codec
    elif suffix in (".xz", ".lzma"):
        import lzma as codec
    else:
        return path.read_text()
    try:
        with codec.open(path, "rt") as handle:
            return handle.read()
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        raise
    except (OSError, EOFError, getattr(codec, "LZMAError", OSError)) as exc:
        raise DimacsError(f"{path.name}: not a valid {suffix} file") from exc


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


# ---------------------------------------------------------------- big integers
def _without_digit_limit(convert, value):
    """Apply ``str`` or ``int`` without Python's 4300-digit conversion limit.

    Model counts routinely exceed it: 15000 unconstrained variables already do.
    """
    if not hasattr(sys, "set_int_max_str_digits"):
        return convert(value)
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        return convert(value)
    finally:
        sys.set_int_max_str_digits(previous)


def to_decimal(value: int) -> str:
    return _without_digit_limit(str, value)


def from_decimal(text: str) -> int:
    return _without_digit_limit(int, text)


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
        # An empty equation with rhs 1 is a contradiction: emit yields the empty clause.
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


def _insert_variable(table: list[int], position: int) -> list[int]:
    """The same function with one more variable, at bit ``position`` of the index."""
    block = 1 << position
    out: list[int] = []
    for start in range(0, len(table), block):
        piece = table[start : start + block]
        out += piece
        out += piece
    return out


def _sum_out(table: list[int], position: int) -> list[int]:
    """Sum over the variable at bit ``position`` of the index."""
    block = 1 << position
    out: list[int] = []
    for start in range(0, len(table), 2 * block):
        low = table[start : start + block]
        high = table[start + block : start + 2 * block]
        out += [a + b for a, b in zip(low, high)]
    return out


def count_elimination(problem: Problem) -> int:
    """Exact counting by variable elimination over clause tables.

    Fast when the formula has a narrow elimination order (chains, grids, trees)
    and refused when a step would need a table over more than
    ``ELIMINATION_MAX_SCOPE`` variables. It shares only the XOR encoding with
    the Ganak and DPLL engines.
    """
    if _trivially_unsatisfiable(problem):
        return 0
    clauses, total = encode_xors(problem)

    # One 0/1 table per distinct clause scope; index bit i belongs to scope[i].
    tables: dict[tuple[int, ...], list[int]] = {}
    for clause in clauses:
        clause = _clause(list(clause))
        if clause is None:  # a tautology constrains nothing
            continue
        scope = tuple(sorted(abs(literal) for literal in clause))
        if len(scope) > ELIMINATION_MAX_SCOPE:
            raise EngineSkipped(f"a clause has more than {ELIMINATION_MAX_SCOPE} variables")
        falsifying = sum(1 << scope.index(-l) for l in clause if l < 0)
        table = tables.setdefault(scope, [1] * (1 << len(scope)))
        table[falsifying] = 0  # the one assignment of the scope that falsifies the clause

    factors: dict[int, tuple[tuple[int, ...], list[int]]] = dict(enumerate(tables.items()))
    next_id = len(factors)
    touching: dict[int, set[int]] = {}
    for identifier, (scope, _) in factors.items():
        for variable in scope:
            touching.setdefault(variable, set()).add(identifier)

    kept = None if problem.projection is None else set(problem.projection)
    counted = range(1, total + 1) if kept is None else kept
    free = sum(1 for variable in counted if variable not in touching)
    scalar = 1

    def joined_scope(variable: int) -> set[int]:
        scope: set[int] = set()
        for identifier in touching[variable]:
            scope.update(factors[identifier][0])
        return scope

    def eliminate(variables: list[int]) -> None:
        nonlocal next_id, scalar
        pending = set(variables)
        heap = [(len(joined_scope(v)), v) for v in pending]
        heapq.heapify(heap)
        while pending:
            size, variable = heapq.heappop(heap)
            if variable not in pending:
                continue
            scope_set = joined_scope(variable)
            if len(scope_set) != size:  # stale entry: the neighbourhood changed
                heapq.heappush(heap, (len(scope_set), variable))
                continue
            if size > ELIMINATION_MAX_SCOPE:
                raise EngineSkipped(
                    f"elimination needs a table over more than {ELIMINATION_MAX_SCOPE} variables"
                )
            scope = sorted(scope_set)
            product = [1] * (1 << len(scope))
            for identifier in list(touching[variable]):
                factor_scope, table = factors.pop(identifier)
                for other in factor_scope:
                    touching[other].discard(identifier)
                present = set(factor_scope)
                for position, name in enumerate(scope):
                    if name not in present:
                        table = _insert_variable(table, position)
                product = [a * b for a, b in zip(product, table)]
            summed = _sum_out(product, scope.index(variable))
            scope.remove(variable)
            pending.discard(variable)
            del touching[variable]
            if scope:
                factors[next_id] = (tuple(scope), summed)
                for other in scope:
                    touching[other].add(next_id)
                    if other in pending:
                        heapq.heappush(heap, (len(joined_scope(other)), other))
                next_id += 1
            else:
                scalar *= summed[0]

    if kept is None:
        eliminate(list(touching))
    else:
        eliminate([variable for variable in touching if variable not in kept])
        # Every hidden variable is gone. A projected assignment counts once when it
        # has any extension, and a product is nonzero exactly when each factor is.
        scalar = 1 if scalar else 0
        for identifier, (scope, table) in factors.items():
            factors[identifier] = (scope, [1 if value else 0 for value in table])
        eliminate(list(touching))
    return scalar << free


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
    return from_decimal(result["count"])


ENGINES = {
    "ganak": count_ganak,
    "bitset": count_bitset,
    "elimination": count_elimination,
    "veritas": count_veritas,
    "dpll": count_dpll,
}
# The module each optional engine needs. For veritas this is the R9.12 counting
# module: older releases of the package, such as v3.8.2, do not have it.
_REQUIRED_MODULES = {"ganak": "pyganak", "veritas": "veritas.research.gf2_xor_count"}


def _module_present(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:  # a missing or broken parent package
        return False


def engine_availability() -> dict[str, str | None]:
    """Engine name to ``None`` when usable, otherwise the reason it is not."""
    status: dict[str, str | None] = {}
    for name in ENGINES:
        module = _REQUIRED_MODULES.get(name)
        missing = module is not None and not _module_present(module)
        status[name] = f"{module} is not importable" if missing else None
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
    chosen.append("elimination")
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

    @property
    def count_digits(self) -> int | None:
        return None if self.count is None else len(self.count)

    @property
    def count_bits(self) -> int | None:
        """Bit length of the count: it lies in [2**(bits-1), 2**bits)."""
        return None if self.count is None else from_decimal(self.count).bit_length()

    def to_json(self) -> dict:
        data = asdict(self)
        data["count_digits"] = self.count_digits
        data["count_bits"] = self.count_bits
        data["cross_checked"] = self.cross_checked
        data["subexponential_claim"] = False
        return data


def _execute(name: str, problem: Problem) -> tuple[str, str]:
    try:
        # The limit is lifted around the engine too: pyganak builds its result from a
        # decimal string, so a large count would otherwise fail inside the engine.
        return "ok", _without_digit_limit(lambda p: str(ENGINES[name](p)), problem)
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


def _payload(problem: Problem) -> str:
    return json.dumps(
        {
            "num_variables": problem.num_variables,
            "clauses": problem.clauses,
            "xors": problem.xors,
            "projection": problem.projection,
        }
    )


def _child_environment() -> dict[str, str]:
    # The child must import this package however the parent found it.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(entry or os.getcwd() for entry in sys.path)
    return environment


def _read_result(output: str, returncode: int | None) -> tuple[str, str]:
    marked = [line for line in output.splitlines() if line.startswith(_RESULT_MARK)]
    if not marked:
        return "error", f"engine process exited with code {returncode} and no result"
    status, detail = json.loads(marked[-1][len(_RESULT_MARK) :])
    return status, detail


def _engine_run(name: str, status: str, payload: str, seconds: float) -> EngineRun:
    if status == "ok":
        return EngineRun(name, "ok", payload, round(seconds, 3))
    return EngineRun(name, status, None, round(seconds, 3), payload)


def run_engine(name: str, problem: Problem, timeout: float, *, isolate: bool = True) -> EngineRun:
    """Run one engine, in its own process with a hard wall-clock limit when isolated."""
    if isolate:
        return run_engines([name], problem, timeout=timeout, verify_timeout=timeout)[0]
    started = monotonic()
    status, payload = _execute(name, problem)
    return _engine_run(name, status, payload, monotonic() - started)


def run_engines(
    names: list[str],
    problem: Problem,
    *,
    timeout: float,
    verify_timeout: float,
    jobs: int | None = None,
) -> list[EngineRun]:
    """Run engines in separate processes, up to ``jobs`` at a time.

    An engine is stopped once it has run for ``timeout`` seconds. When the
    first count arrives, engines still running get ``verify_timeout`` more
    seconds, and engines started later get ``verify_timeout`` seconds in all.
    Results come back in the order given.
    """
    if jobs is None:
        jobs = min(len(names), os.cpu_count() or 1)
    jobs = max(1, jobs)
    environment = _child_environment()
    results: dict[str, EngineRun] = {}
    waiting = list(names)
    running: dict[str, tuple[subprocess.Popen, float, object]] = {}
    payload_text = _payload(problem)
    first_count_at: float | None = None
    pause = 0.002
    try:
        while waiting or running:
            while waiting and len(running) < jobs:
                name = waiting.pop(0)
                # Each child gets its own input file: a shared handle would share
                # one read position between processes.
                with tempfile.TemporaryFile("w+") as problem_file:
                    problem_file.write(payload_text)
                    problem_file.flush()
                    problem_file.seek(0)
                    output = tempfile.TemporaryFile("w+")
                    process = subprocess.Popen(
                        [sys.executable, "-c", _WORKER, name],
                        stdin=problem_file,
                        stdout=output,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        env=environment,
                    )
                running[name] = (process, monotonic(), output)
            for name, (process, started, output) in list(running.items()):
                now = monotonic()
                elapsed = now - started
                # Time this engine has had since a count first existed.
                grace = None if first_count_at is None else now - max(first_count_at, started)
                if process.poll() is not None:
                    output.seek(0)
                    status, payload = _read_result(output.read(), process.returncode)
                elif elapsed >= timeout:
                    process.kill()
                    process.wait()
                    status, payload = "timeout", f"no result within {timeout:g}s"
                elif grace is not None and grace >= verify_timeout:
                    process.kill()
                    process.wait()
                    status = "timeout"
                    payload = f"stopped {verify_timeout:g}s after another engine finished"
                else:
                    continue
                output.close()
                del running[name]
                results[name] = _engine_run(name, status, payload, elapsed)
                if status == "ok" and first_count_at is None:
                    first_count_at = monotonic()
                pause = 0.002
            if running:
                sleep(pause)
                pause = min(pause * 1.5, 0.05)
    finally:
        for process, _, output in running.values():
            process.kill()
            process.wait()
            output.close()
    return [results[name] for name in names]


def count_models(
    problem: Problem,
    *,
    engines: str | list[str] = "auto",
    timeout: float = 60.0,
    verify_timeout: float = 10.0,
    verify: bool = True,
    isolate: bool = True,
    jobs: int | None = None,
) -> CountResult:
    """Count models with every planned engine and compare the counts.

    Isolated engines run side by side, ``jobs`` at a time (one per processor by
    default). ``timeout`` bounds each engine; once one engine has a count the
    rest get ``verify_timeout`` more seconds. With
    ``isolate=False`` the engines run in this process, one after another, with
    no time limit.
    """
    if timeout <= 0 or verify_timeout <= 0:
        raise ValueError("timeouts must be positive")
    if jobs is not None and jobs < 1:
        raise ValueError("jobs must be at least 1")
    names = plan_engines(problem, engines)
    if not verify:
        names = names[:1]
    if isolate:
        runs = run_engines(
            names, problem, timeout=timeout, verify_timeout=verify_timeout, jobs=jobs
        )
    else:
        runs = [run_engine(name, problem, timeout, isolate=False) for name in names]
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
    parser.add_argument(
        "input", nargs="?", help="DIMACS file (.gz, .bz2 and .xz are read), or - for standard input"
    )
    parser.add_argument(
        "--engines",
        default="auto",
        help=f"comma-separated subset of {','.join(ENGINES)}",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="seconds allowed per engine")
    parser.add_argument(
        "--verify-timeout",
        type=float,
        default=10.0,
        help="extra seconds the other engines get once one engine has a count",
    )
    parser.add_argument(
        "--jobs", type=int, default=None, help="engines to run at once (default: one per processor)"
    )
    parser.add_argument("--no-verify", action="store_true", help="run the first engine only")
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
        if result.count_digits > 20:
            head += f", {result.count_digits} digits, below 2^{result.count_bits}"
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
        text = sys.stdin.read() if args.input == "-" else read_text(args.input)
        problem = parse_dimacs(text)
        result = count_models(
            problem,
            engines=args.engines,
            timeout=args.timeout,
            verify_timeout=args.verify_timeout,
            verify=not args.no_verify,
            jobs=args.jobs,
        )
    except (OSError, EOFError, UnicodeDecodeError, ValueError) as exc:
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

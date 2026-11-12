"""Optional external exact counters vs internal structure/hybrid paths."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from time import perf_counter

from veritas.core.cnf import CNF
from veritas.solvers.ganak import CounterUnavailable, exact_count as ganak_count
from veritas.solvers.reference import exhaustive_count


class BaselineUnavailable(Exception):
    pass


def cryptominisat_count(cnf: CNF, *, seconds: float = 30.0, executable: str | None = None) -> int | dict:
    binary = executable or os.environ.get('VERITAS_CRYPTOMINISAT') or shutil.which('cryptominisat5')
    if not binary:
        return {'unavailable': 'cryptominisat5 not on PATH'}
    with tempfile.TemporaryDirectory(prefix='veritas_cryptominisat_') as root:
        path = os.path.join(root, 'query.cnf')
        with open(path, 'w', encoding='ascii') as handle:
            handle.write(cnf.to_dimacs())
        try:
            proc = subprocess.run(
                [binary, '--verb', '0', '--maxtime', str(int(seconds)), path],
                capture_output=True,
                text=True,
                timeout=seconds + 2,
                cwd=root,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {'unavailable': str(exc)}
        for line in proc.stdout.splitlines() + proc.stderr.splitlines():
            line = line.strip()
            if line.startswith('s mc '):
                try:
                    return int(line.split()[-1])
                except ValueError:
                    continue
        if proc.returncode == 10:
            return 0
        return {'unavailable': 'could not parse CryptoMiniSat model count output'}


def cadical_sat(cnf: CNF, *, seconds: float = 10.0, executable: str | None = None) -> bool | None:
    """Return True/False if CADICAL decides SAT; None if binary missing."""
    binary = executable or os.environ.get('VERITAS_CADICAL') or shutil.which('cadical')
    if not binary:
        return None
    with tempfile.TemporaryDirectory(prefix='veritas_cadical_') as root:
        path = os.path.join(root, 'query.cnf')
        with open(path, 'w', encoding='ascii') as handle:
            handle.write(cnf.to_dimacs())
        try:
            proc = subprocess.run(
                [binary, path],
                capture_output=True,
                text=True,
                timeout=seconds,
                cwd=root,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode == 10:
            return True
        if proc.returncode == 20:
            return False
        if proc.returncode not in (0,):
            return None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line == 's UNSATISFIABLE':
                return False
            if line in ('s SATISFIABLE', 's TRUE'):
                return True
        return None


def cadical_enumerate_count(cnf: CNF, *, max_models: int = 1_000_000, seconds: float = 30.0) -> int | dict:
    """Count models by blocking-clause iteration when CADICAL is available (exact, capped)."""
    binary = os.environ.get('VERITAS_CADICAL') or shutil.which('cadical')
    if not binary:
        return {'unavailable': 'cadical not on PATH'}
    total = 0
    blocker: list[int] = []
    with tempfile.TemporaryDirectory(prefix='veritas_cadical_enum_') as root:
        while total < max_models:
            path = os.path.join(root, 'query.cnf')
            lines = [f'p cnf {cnf.n} {len(cnf.clauses) + len(blocker)}']
            for cl in cnf.clauses:
                lines.append(' '.join(map(str, cl)) + ' 0')
            for cl in blocker:
                lines.append(' '.join(map(str, cl)) + ' 0')
            with open(path, 'w', encoding='ascii') as handle:
                handle.write('\n'.join(lines) + '\n')
            try:
                proc = subprocess.run(
                    [binary, path],
                    capture_output=True,
                    text=True,
                    timeout=seconds,
                    cwd=root,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return {'unavailable': str(exc)}
            if proc.returncode == 20:
                return total
            model: dict[int, bool] | None = None
            for line in proc.stdout.splitlines():
                if line.startswith('v '):
                    parts = [int(x) for x in line.split()[1:] if x != '0']
                    model = {abs(v): v > 0 for v in parts}
            if model is None or proc.returncode not in (10, 0):
                return {'unavailable': 'cadical did not return a model'}
            if not cnf.evaluate(model):
                return {'unavailable': 'cadical model failed CNF check'}
            total += 1
            blocker.append(tuple(-v if model[v] else v for v in range(1, cnf.n + 1)))
    return {'unavailable': f'exceeded cadical enumerate cap {max_models}'}


def compare_count_baselines(cnf: CNF, structure_fn, **kwargs) -> dict:
    """Cross-check structure/hybrid counting with exhaustive and optional Ganak."""
    start = perf_counter()
    internal = structure_fn(cnf, **kwargs)
    internal_seconds = perf_counter() - start
    xor_equations = kwargs.get('xor_equations')
    row = {
        'formula_sha256': cnf.digest(),
        'n': cnf.n,
        'clauses': len(cnf.clauses),
        'xor_equation_count': len(xor_equations) if xor_equations else 0,
        'internal_count': int(internal['count']),
        'internal_engine': internal.get('engine'),
        'internal_independent_count_checked': internal.get('independent_count_checked'),
        'internal_seconds': round(internal_seconds, 6),
        'exhaustive_count': None,
        'ganak_count': None,
        'cadical_sat': None,
        'cadical_enum_count': None,
        'cryptominisat_count': None,
        'all_match': False,
        'complexity_claim': False,
    }
    if cnf.n <= 18:
        row['exhaustive_count'] = exhaustive_count(cnf)
    try:
        row['ganak_count'] = ganak_count(cnf)
    except CounterUnavailable as exc:
        row['ganak_count'] = {'unavailable': str(exc)}
    row['cadical_sat'] = cadical_sat(cnf)
    if cnf.n <= 22 and len(cnf.clauses) <= 2000:
        row['cadical_enum_count'] = cadical_enumerate_count(cnf)
    row['cryptominisat_count'] = cryptominisat_count(cnf)
    matches = [row['internal_count']]
    if row['exhaustive_count'] is not None:
        matches.append(row['exhaustive_count'])
    if type(row['ganak_count']) is int:
        matches.append(row['ganak_count'])
    if type(row['cryptominisat_count']) is int:
        matches.append(row['cryptominisat_count'])
    if type(row['cadical_enum_count']) is int:
        matches.append(row['cadical_enum_count'])
    row['all_match'] = len(set(matches)) == 1
    return row

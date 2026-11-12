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


def compare_count_baselines(cnf: CNF, structure_fn, **kwargs) -> dict:
    """Cross-check structure/hybrid counting with exhaustive and optional Ganak."""
    start = perf_counter()
    internal = structure_fn(cnf, **kwargs)
    internal_seconds = perf_counter() - start
    row = {
        'formula_sha256': cnf.digest(),
        'n': cnf.n,
        'clauses': len(cnf.clauses),
        'internal_count': int(internal['count']),
        'internal_engine': internal.get('engine'),
        'internal_seconds': round(internal_seconds, 6),
        'exhaustive_count': None,
        'ganak_count': None,
        'cadical_sat': None,
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
    matches = [row['internal_count']]
    if row['exhaustive_count'] is not None:
        matches.append(row['exhaustive_count'])
    if type(row['ganak_count']) is int:
        matches.append(row['ganak_count'])
    row['all_match'] = len(set(matches)) == 1
    return row

#!/usr/bin/env python3
"""Research gates: residual equivalence counts and v34 benchmark consistency."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'benchmarks'))

from residual_benchmark_cnfs import all_family_builders
from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import count_with_residual_memo, prefix_residual_table
from veritas.solvers.reference import exhaustive_count


def _block_gate() -> dict:
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    count, _, _ = count_with_residual_memo(cnf, preprocess=True)
    buckets = prefix_residual_table(cnf, (1, 2))
    mults = sorted(b['multiplicity'] for b in buckets)
    return {
        'count': count,
        'exhaustive': exhaustive_count(cnf),
        'prefix_buckets': len(buckets),
        'prefix_multiplicities': mults,
        'ok': count == 5 and mults == [1, 3],
    }


def _v34_smoke() -> dict:
    failures: list[str] = []
    from v34_residual_growth import row

    for name, builder in all_family_builders().items():
        metrics = row(name, builder())
        if metrics.get('skipped'):
            continue
        check = metrics.get('exhaustive_check')
        if check is not None and check != metrics.get('count'):
            failures.append(f'{name}: residual={metrics.get("count")} exhaustive={check}')
    return {
        'cases_checked': len(all_family_builders()),
        'failures': failures,
        'ok': not failures,
    }


def main() -> int:
    out = ROOT / 'validation' / 'residual_gates.json'
    report = {
        'schema': 'VERITAS_RESIDUAL_GATES_V1',
        'block_example': _block_gate(),
        'v34_exhaustive_smoke': _v34_smoke(),
        'complexity_claim': False,
        'release_ready': {},
    }
    report['release_ready'] = {
        'block_example': report['block_example']['ok'],
        'v34_exhaustive_smoke': report['v34_exhaustive_smoke']['ok'],
    }
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    ok = all(report['release_ready'].values())
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
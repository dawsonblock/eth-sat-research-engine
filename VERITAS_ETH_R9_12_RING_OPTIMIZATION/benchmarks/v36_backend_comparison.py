"""Compare hybrid vs residual memo backends on the v34 case suite."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'benchmarks'))

from residual_benchmark_cnfs import all_family_builders
from veritas.research.cnf_structure import structure_aware_count


def row(name: str, cnf) -> dict:
    dual = structure_aware_count(
        cnf,
        preprocess=True,
        count_backend='dual',
        timeout_s=10,
        verify_direct=False,
    )
    cmp = dual.get('ledger_comparison') or {}
    residual = dual.get('residual_research') or {}
    return {
        'name': name,
        'n': cnf.n,
        'count': dual.get('count'),
        'hybrid_engine': dual.get('engine'),
        'ledger_comparison': cmp,
        'residual_distinct_states': residual.get('distinct_residual_states'),
        'complexity_claim': False,
    }


if __name__ == '__main__':
    builders = all_family_builders()
    report = {
        'schema': 'VERITAS_BACKEND_COMPARE_V36',
        'rows': [row(n, b()) for n, b in builders.items() if b().n <= 22],
    }
    out = ROOT / 'validation' / 'backend_compare_v36.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
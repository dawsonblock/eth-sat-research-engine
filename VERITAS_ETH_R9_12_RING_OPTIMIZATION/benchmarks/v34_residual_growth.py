"""Measure distinct residual fingerprints vs brute 2^n on small CNFs."""
from __future__ import annotations

import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import count_with_residual_memo
from veritas.solvers.reference import exhaustive_count

CASES = {
    'block_xy_z': CNF.from_lists(3, [[1, 3], [2, 3]]),
    'path_4': CNF.from_lists(4, [[1, 2], [2, 3], [3, 4]]),
    'two_components': CNF.from_lists(4, [[1, 2], [3, 4]]),
}


def row(cnf: CNF) -> dict:
    count, stats, report = count_with_residual_memo(cnf, preprocess=True)
    brute = 2**cnf.n
    return {
        'n': cnf.n,
        'clauses': len(cnf.clauses),
        'count': count,
        'exhaustive_check': exhaustive_count(cnf) if cnf.n <= 18 else None,
        'brute_assignments': brute,
        'distinct_residual_states': stats.distinct_residual_states,
        'cache_hits': stats.cache_hits,
        'recursive_calls': stats.recursive_calls,
        'compression_ratio_states_vs_brute': round(brute / max(1, stats.distinct_residual_states), 4),
        'memo_reuse_ratio': report.get('memo_reuse_ratio'),
        'complexity_claim': False,
    }


if __name__ == '__main__':
    report = {
        'schema': 'VERITAS_RESIDUAL_GROWTH_V34',
        'cases': list(CASES),
        'rows': [row(cnf) for cnf in CASES.values()],
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'residual_growth_v34.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

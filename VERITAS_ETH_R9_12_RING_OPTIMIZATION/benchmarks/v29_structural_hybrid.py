"""Structural decomposition vs direct hybrid routing (small instances only)."""
from __future__ import annotations

import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.hybrid_router import hybrid_count
from veritas.solvers.reference import exhaustive_count

CASES = {
    'two_clauses_disconnected': CNF.from_lists(4, [[1, 2], [3, 4]]),
    'path_connected': CNF.from_lists(4, [[1, 2], [2, 3], [3, 4]]),
    'two_chains': CNF.from_lists(6, [[1, 2], [2, 3], [4, 5], [5, 6]]),
}


def main() -> None:
    rows = []
    for name, cnf in CASES.items():
        direct = hybrid_count(cnf, timeout_s=10)
        structured = structure_aware_count(cnf, timeout_s=10, verify_direct=True)
        rows.append(
            {
                'case': name,
                'n': cnf.n,
                'exhaustive': exhaustive_count(cnf),
                'direct_count': direct['count'],
                'structured_count': structured['count'],
                'decomposed': structured['structure']['decomposed'],
                'direct_engine': direct.get('engine'),
                'structured_engine': structured.get('engine'),
                'matches_exhaustive': str(exhaustive_count(cnf)) == structured['count'],
            }
        )
    report = {
        'schema': 'VERITAS_STRUCTURAL_HYBRID_V1',
        'warning': 'Planner estimates only; not competition-grade benchmarking.',
        'results': rows,
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'structural_hybrid_v29.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

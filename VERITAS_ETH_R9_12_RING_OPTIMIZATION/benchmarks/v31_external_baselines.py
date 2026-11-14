"""Compare structure/hybrid counts with exhaustive and optional Ganak/CADICAL."""
from __future__ import annotations

import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.solvers.external_baselines import compare_count_baselines

CASES = {
    'two_disconnected': CNF.from_lists(4, [[1, 2], [3, 4]]),
    'path_4': CNF.from_lists(4, [[1, 2], [2, 3], [3, 4]]),
}

if __name__ == '__main__':
    rows = [
        compare_count_baselines(cnf, structure_aware_count, timeout_s=10, preprocess=True)
        for cnf in CASES.values()
    ]
    report = {
        'schema': 'VERITAS_EXTERNAL_BASELINES_V31',
        'cases': list(CASES),
        'rows': rows,
        'ganak_required_for_full_gate': False,
        'complexity_claim': False,
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'external_baselines_v31.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

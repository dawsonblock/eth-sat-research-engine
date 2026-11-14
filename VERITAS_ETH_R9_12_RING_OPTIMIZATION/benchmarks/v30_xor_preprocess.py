"""GF(2) XOR and preprocessing pipeline smoke checks."""
from __future__ import annotations

import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, xor_chain_example
from veritas.research.cnf_structure import structure_aware_count
from veritas.solvers.reference import exhaustive_count

if __name__ == '__main__':
    eqs, n = xor_chain_example()
    pure = structure_aware_count(CNF.from_lists(n, []), xor_equations=eqs, preprocess=False)
    rows = [
        {
            'case': 'pure_xor_chain',
            'engine': pure['engine'],
            'count': pure['count'],
        },
        {
            'case': 'preprocess_plus_components',
            'count': structure_aware_count(
                CNF.from_lists(4, [[1], [1, 2], [3, 4]]), preprocess=True, timeout_s=10
            )['count'],
            'exhaustive': exhaustive_count(CNF.from_lists(4, [[1], [1, 2], [3, 4]])),
        },
    ]
    assert rows[0]['count'] == '2'
    assert int(rows[1]['count']) == rows[1]['exhaustive']
    report = {'schema': 'VERITAS_XOR_PREPROCESS_V30', 'rows': rows, 'complexity_claim': False}
    path = Path(__file__).resolve().parents[1] / 'validation' / 'xor_preprocess_v30.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

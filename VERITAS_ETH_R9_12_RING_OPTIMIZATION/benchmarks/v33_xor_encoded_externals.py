"""Mixed XOR: internal count vs exhaustive / encoded CNF external baselines."""
from __future__ import annotations

import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.gf2_xor_count import XorEquation
from veritas.solvers.external_baselines import compare_count_baselines

CASES = {
    'encode_small': (
        CNF.from_lists(3, [[1, 3]]),
        (XorEquation((1, 2), 1),),
        {'xor_strategy': 'encode', 'preprocess': False},
    ),
    'condition_small': (
        CNF.from_lists(3, [[1, 3]]),
        (XorEquation((1, 2), 1),),
        {'xor_strategy': 'condition', 'preprocess': False},
    ),
}

if __name__ == '__main__':
    rows = []
    for name, (cnf, eqs, opts) in CASES.items():
        rows.append(
            {
                **compare_count_baselines(
                    cnf,
                    structure_aware_count,
                    xor_equations=eqs,
                    verify_direct=True,
                    timeout_s=10,
                    **opts,
                ),
                'case': name,
            }
        )
    report = {
        'schema': 'VERITAS_XOR_ENCODED_EXTERNALS_V33',
        'rows': rows,
        'note': 'ganak_encoded_count requires Ganak on PATH; unavailable is not failure',
        'complexity_claim': False,
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'xor_encoded_externals_v33.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

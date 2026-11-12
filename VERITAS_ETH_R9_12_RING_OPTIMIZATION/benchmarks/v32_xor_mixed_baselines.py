"""Mixed CNF+XOR counts with structure paths and optional external baselines."""
from __future__ import annotations

import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.gf2_xor_count import XorEquation
from veritas.solvers.external_baselines import compare_count_baselines

CASES = {
    'binary_fast_path': (
        CNF.from_lists(3, [[1, 3]]),
        (XorEquation((1, 2), 1),),
    ),
    'component_product': (
        CNF.from_lists(4, [[1, 2], [3, 4]]),
        (XorEquation((1, 2), 0),),
    ),
    'mixed_condition': (
        CNF.from_lists(3, [[1, 3]]),
        (XorEquation((1, 2, 3), 1),),
    ),
    'encode_path': (
        CNF.from_lists(3, [[1, 3]]),
        (XorEquation((1, 2), 1),),
    ),
}

ENCODE_CASE = CASES['encode_path']

if __name__ == '__main__':
    rows = []
    cnf_e, eqs_e = ENCODE_CASE
    rows.append(
        {
            **compare_count_baselines(
                cnf_e,
                structure_aware_count,
                xor_equations=eqs_e,
                preprocess=False,
                xor_strategy='encode',
                verify_direct=True,
                timeout_s=10,
            ),
            'case': 'encode_path',
        }
    )
    for name, (cnf, eqs) in CASES.items():
        if name == 'encode_path':
            continue
        rows.append(
            compare_count_baselines(
                cnf,
                structure_aware_count,
                xor_equations=eqs,
                preprocess=False,
                verify_direct=True,
                timeout_s=10,
            )
        )
        rows[-1]['case'] = name
    report = {
        'schema': 'VERITAS_XOR_MIXED_BASELINES_V32',
        'cases': list(CASES),
        'rows': rows,
        'complexity_claim': False,
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'xor_mixed_baselines_v32.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

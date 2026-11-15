#!/usr/bin/env python3
"""Phase-0/1 gates for computational cost reduction (engineering, not theorems)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from veritas.research.anthropic_eight_square import verify_crossing_identity_12, verify_identity_28
from veritas.research.anthropic_signed_contraction import crossing_rewrite_economics
from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
from veritas.research.gf2_xor_substitute import substitute_binary_xor


def _xor_substitute_gate() -> dict:
    cnf = CNF.from_lists(3, [[2, 3]])
    eqs = (XorEquation((1, 2), 1),)
    reduced, eqs2, sub = substitute_binary_xor(cnf, eqs)
    pipeline = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, verify_direct=True)
    return {
        'binary_substitute_changed': sub.get('changed'),
        'reduced_n': reduced.n,
        'pipeline_count': pipeline.get('count'),
        'matches_three': pipeline.get('count') == '3',
    }


def main() -> int:
    out = ROOT / 'validation' / 'cost_reduction_gates.json'
    report = {
        'schema': 'VERITAS_COST_REDUCTION_GATES_V1',
        'equation_12': verify_crossing_identity_12(),
        'equation_28': verify_identity_28(),
        'signed_one_level': crossing_rewrite_economics(),
        'xor_algebraic_substitute': _xor_substitute_gate(),
        'release_ready': {
            'eight_square_4096': None,
            'pair_identity_exhaustive': None,
            'xor_mixed_smoke': None,
            'unsupported_worst_case_claim': False,
        },
    }
    report['release_ready']['eight_square_4096'] = report['equation_12']['failures'] == 0
    report['release_ready']['pair_identity_exhaustive'] = report['equation_28']['failures'] == 0
    report['release_ready']['xor_mixed_smoke'] = report['xor_algebraic_substitute']['matches_three']
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    ok = all(
        report['release_ready'][k]
        for k in ('eight_square_4096', 'pair_identity_exhaustive', 'xor_mixed_smoke')
    )
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())

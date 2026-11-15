"""Hybrid evaluated-assignment work vs distinct residual states (v37)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'benchmarks'))

from v36_backend_comparison import row
from residual_benchmark_cnfs import all_family_builders


def summarize(entry: dict) -> dict:
    cmp = entry.get('ledger_comparison') or {}
    hybrid_work = cmp.get('hybrid_evaluated_assignments')
    states = cmp.get('residual_distinct_states')
    ratio = cmp.get('hybrid_work_per_residual_state')
    if ratio is None and hybrid_work is not None and states:
        ratio = round(hybrid_work / states, 4)
    return {
        'name': entry['name'],
        'n': entry['n'],
        'hybrid_evaluated_assignments': hybrid_work,
        'residual_distinct_states': states,
        'hybrid_work_per_residual_state': ratio,
        'residual_compression_vs_brute': cmp.get('residual_compression_vs_brute'),
        'counts_match': cmp.get('counts_match'),
        'complexity_claim': False,
    }


if __name__ == '__main__':
    builders = all_family_builders()
    rows = [summarize(row(name, b())) for name, b in builders.items() if b().n <= 22]
    work_ratios = [r['hybrid_work_per_residual_state'] for r in rows if r['hybrid_work_per_residual_state']]
    report = {
        'schema': 'VERITAS_WORK_PER_RESIDUAL_STATE_V37',
        'rows': rows,
        'summary': {
            'cases': len(rows),
            'max_hybrid_work_per_state': max(work_ratios) if work_ratios else None,
            'min_hybrid_work_per_state': min(work_ratios) if work_ratios else None,
        },
        'complexity_claim': False,
    }
    out = ROOT / 'validation' / 'work_per_residual_state_v37.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
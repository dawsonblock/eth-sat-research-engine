"""Measure distinct residual fingerprints vs brute 2^n on small CNFs."""
from __future__ import annotations

import json
from pathlib import Path

from pathlib import Path as _Path

import sys as _sys

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from residual_benchmark_cnfs import all_family_builders
from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import residual_research_metrics
from veritas.solvers.reference import exhaustive_count


def row(name: str, cnf: CNF) -> dict:
    metrics = residual_research_metrics(cnf, preprocess=True, max_n=22, prefix_depth=min(12, cnf.n))
    if metrics.get('skipped'):
        return {'name': name, **metrics}
    return {
        'name': name,
        'n': cnf.n,
        'clauses': len(cnf.clauses),
        'count': metrics['count'],
        'exhaustive_check': exhaustive_count(cnf) if cnf.n <= 18 else None,
        'brute_assignments': metrics['brute_assignments'],
        'distinct_residual_states': metrics['distinct_residual_states'],
        'cache_hits': metrics['cache_hits'],
        'recursive_calls': metrics['recursive_calls'],
        'compression_ratio_states_vs_brute': metrics['compression_ratio_states_vs_brute'],
        'memo_reuse_ratio': metrics.get('memo_reuse_ratio'),
        'prefix_equivalence_buckets': metrics['prefix_equivalence_buckets'],
        'prefix_multiplicity_histogram': metrics['prefix_multiplicity_histogram'],
        'family': _family_tag(name),
        'complexity_claim': False,
    }


def _family_tag(name: str) -> str:
    if 'random' in name or 'pigeon' in name or 'tight_primed' in name:
        return 'adversarial'
    if 'independent' in name or 'two_' in name:
        return 'independent'
    if 'dimacs' in name:
        return 'archive'
    if 'network' in name or 'star' in name or 'layered' in name or 'coupled' in name:
        return 'coupled'
    return 'structured'


if __name__ == '__main__':
    builders = all_family_builders()
    report = {
        'schema': 'VERITAS_RESIDUAL_GROWTH_V34',
        'families': ['structured', 'independent', 'coupled', 'adversarial', 'archive'],
        'cases': list(builders),
        'rows': [row(name, builder()) for name, builder in builders.items()],
    }
    path = Path(__file__).resolve().parents[1] / 'validation' / 'residual_growth_v34.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

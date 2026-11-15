"""Exact #SAT via residual CNF memoization (research backend)."""
from __future__ import annotations

from dataclasses import asdict
from time import monotonic

from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import ResidualStats, count_with_residual_memo


def _strip_hybrid_kwargs(kwargs: dict) -> tuple[bool, dict]:
    preprocess = kwargs.pop('preprocess', True)
    ignored = {
        k: kwargs.pop(k, None)
        for k in list(kwargs)
        if k
        not in (
            'verify_direct',
            'timeout_s',
            'preprocess',
        )
    }
    return preprocess, ignored


def residual_research_count(cnf: CNF, **kwargs) -> dict:
    """Research exact counter using Shannon + residual fingerprint memo."""
    start = monotonic()
    preprocess, ignored = _strip_hybrid_kwargs(dict(kwargs))
    count, stats, report = count_with_residual_memo(cnf, preprocess=preprocess)
    elapsed = monotonic() - start
    residual = {
        **report,
        **asdict(stats),
    }
    return {
        'status': 'EXACT_COUNT',
        'count': str(count),
        'engine': 'EXACT_RESIDUAL_MEMO_SHANNON',
        'formula_sha256': cnf.digest(),
        'execution': {
            'distinct_residual_states': stats.distinct_residual_states,
            'cache_hits': stats.cache_hits,
            'recursive_calls': stats.recursive_calls,
            'max_depth': stats.max_depth,
            'memo_reuse_ratio': report.get('memo_reuse_ratio'),
            'brute_assignments_upper_bound': 2**cnf.n,
            'method': 'EXACT_RESIDUAL_MEMO_SHANNON',
        },
        'residual_research': residual,
        'ignored_hybrid_routing_kwargs': ignored,
        'independent_count_checked': False,
        'elapsed_seconds': round(elapsed, 6),
        'complexity_claim': False,
        'warning': (
            'Residual memo Shannon backend; exponential worst case on adversarial CNFs. '
            'Not Anthropic/OpenAI subexponential recursion.'
        ),
    }


def ledger_comparison(hybrid_result: dict, residual_metrics: dict) -> dict:
    """Compare residual-state compression with hybrid/boundary execution stats."""
    if residual_metrics.get('skipped'):
        return {'skipped': True, 'reason': residual_metrics.get('reason')}
    execution = hybrid_result.get('execution') or {}
    hybrid_entries = execution.get('cache_entries')
    if hybrid_entries is None:
        hybrid_entries = execution.get('peak_table_entries')
    tree = hybrid_result.get('tree_ledger') or {}
    return {
        'skipped': False,
        'counts_match': str(hybrid_result.get('count')) == str(residual_metrics.get('count')),
        'hybrid_engine': hybrid_result.get('engine'),
        'hybrid_chosen_backend': (hybrid_result.get('routing') or {}).get('chosen_backend'),
        'hybrid_evaluated_assignments': execution.get('evaluated_assignments'),
        'hybrid_cache_entries': hybrid_entries,
        'hybrid_cache_hits': execution.get('cache_hits'),
        'tree_ledger_unique_subproblems': tree.get('unique_subproblems'),
        'tree_ledger_cache_hits': tree.get('cache_hits'),
        'residual_distinct_states': residual_metrics.get('distinct_residual_states'),
        'residual_recursive_calls': residual_metrics.get('recursive_calls'),
        'residual_memo_reuse_ratio': residual_metrics.get('memo_reuse_ratio'),
        'brute_assignments': residual_metrics.get('brute_assignments'),
        'residual_compression_vs_brute': residual_metrics.get('compression_ratio_states_vs_brute'),
        'complexity_claim': False,
    }
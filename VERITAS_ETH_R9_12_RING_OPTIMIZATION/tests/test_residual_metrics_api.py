from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count


def test_structure_hybrid_includes_residual_metrics():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    out = structure_aware_count(
        cnf,
        preprocess=True,
        timeout_s=5,
        verify_direct=True,
        include_residual_metrics=True,
        residual_prefix_depth=2,
    )
    metrics = out['residual_research']
    assert metrics['skipped'] is False
    assert metrics['distinct_residual_states'] >= 2
    assert metrics['prefix_depth'] == 2
    assert metrics['prefix_equivalence_buckets'] == 2
    assert metrics['prefix_multiplicity_histogram']['largest_bucket'] == 3
    assert str(metrics['count']) == out['count']


def test_residual_metrics_skipped_when_n_too_large():
    cnf = CNF.from_lists(4, [[1, 2], [2, 3], [3, 4]])
    out = structure_aware_count(
        cnf,
        timeout_s=5,
        include_residual_metrics=True,
        residual_metrics_max_n=2,
    )
    assert out['residual_research']['skipped'] is True

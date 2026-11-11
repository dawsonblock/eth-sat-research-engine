from veritas.research.anthropic_signed_contraction import crossing_rewrite_economics


def test_one_level_rewrite_proxy_is_finite_and_honest():
    report = crossing_rewrite_economics()
    assert report['active_crossings'] == 64
    assert report['direct_eval_cost_sum'] > report['min_orientation_cost_sum']
    assert report['both_terms_cost_sum'] >= report['direct_eval_cost_sum']
    assert report['subexponential_runtime_proven'] is False

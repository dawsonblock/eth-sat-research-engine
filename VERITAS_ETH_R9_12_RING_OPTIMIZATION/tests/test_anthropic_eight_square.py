from veritas.research.anthropic_eight_square import (
    crossing_lhs,
    crossing_rhs,
    identity_28_holds,
    prefer_row_merge,
    static_merge_bit_costs,
    verify_crossing_identity_12,
    verify_identity_28,
    xor3,
)


def test_crossing_identity_exhaustive_4096():
    report = verify_crossing_identity_12()
    assert report['settings_checked'] == 4096
    assert report['failures'] == 0
    assert report['subexponential_runtime_proven'] is False


def test_pair_identity_exhaustive():
    report = verify_identity_28()
    assert report['failures'] == 0
    assert report['settings_checked'] == 4096


def test_static_merge_prefers_row():
    costs = static_merge_bit_costs()
    assert costs['crossing_bits'] == 6
    assert costs['row_term_bits'] < costs['column_term_bits']
    assert prefer_row_merge()


def test_identity_28_sample():
    p, q, d = (1, 0, 1), (0, 1, 0), (1, 1, 0)
    p_prime, q_prime = xor3(p, d), xor3(q, d)
    assert q != q_prime
    assert identity_28_holds(p, q, p_prime, q_prime)


def test_lhs_rhs_agree_on_manual_case():
    x, y, u, v = (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1)
    assert crossing_lhs(x, y, u, v) == crossing_rhs(x, y, u, v)

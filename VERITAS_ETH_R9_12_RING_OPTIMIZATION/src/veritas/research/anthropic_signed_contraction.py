"""One-level signed crossing rewrite economics (finite proxy only)."""
from __future__ import annotations

from veritas.research.anthropic_eight_square import (
    all_blocks,
    crossing_lhs,
    crossing_terms,
    static_merge_bit_costs,
)


def _bit_eval_cost(bits: int) -> int:
    return 1 << bits


def crossing_rewrite_economics() -> dict:
    """Compare direct crossing evaluation vs rewritten term costs on all active inputs."""
    costs = static_merge_bit_costs()
    direct_bits = costs['crossing_bits']
    row_bits = costs['row_term_bits']
    col_bits = costs['column_term_bits']
    active = 0
    direct_total = 0
    row_only_total = 0
    min_orientation_total = 0
    both_terms_total = 0
    row_wins = 0
    for x in all_blocks():
        for y in all_blocks():
            for u in all_blocks():
                for v in all_blocks():
                    if crossing_lhs(x, y, u, v) == 0:
                        continue
                    active += 1
                    direct_total += _bit_eval_cost(direct_bits)
                    row, col = crossing_terms(x, y, u, v)
                    row_cost = _bit_eval_cost(row_bits) if row else 0
                    col_cost = _bit_eval_cost(col_bits) if col else 0
                    row_only_total += row_cost
                    both_terms_total += row_cost + col_cost
                    if row_cost and col_cost:
                        if row_cost <= col_cost:
                            min_orientation_total += row_cost
                            row_wins += 1
                        else:
                            min_orientation_total += col_cost
                    else:
                        min_orientation_total += row_cost or col_cost
    return {
        'schema': 'ANTHROPIC_SIGNED_ONE_LEVEL_V1',
        'active_crossings': active,
        'direct_eval_cost_sum': direct_total,
        'row_orientation_cost_sum': row_only_total,
        'min_orientation_cost_sum': min_orientation_total,
        'both_terms_cost_sum': both_terms_total,
        'row_cheaper_count': row_wins,
        'expansion_overhead_vs_direct': both_terms_total - direct_total,
        'min_orientation_savings_vs_direct': direct_total - min_orientation_total,
        'claim': 'BIT_ENUMERATION_PROXY_NOT_RUNTIME',
        'subexponential_runtime_proven': False,
    }

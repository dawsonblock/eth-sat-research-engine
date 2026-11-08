"""Finite whole-vertex layouts for explicit, depth-varying packet parameters.

The same balanced labels are repeated across coordinates. This construction
checks actual port loads and child shrinkage, but does not assert the paper's
padded-packet bound or replace its conditional-expectation packing theorem.
"""
from veritas.research.parent_child_r98.model import PacketLayout, canonical
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout


def finite_layout(parent, a, u, budget):
    if type(a) is not int or type(u) is not int or not 1 <= u <= a <= 3:
        raise ValueError('finite layout requires 1<=u<=a<=3')
    base = construct_vertex_shrinking_layout(parent, budget=budget)
    if (a, u) == (1, 1):
        return base
    src = base.source
    L = 1 << a
    src.update(a=a, L=L, D=64**(2*a),
        H_pad=L*max((p['index']+1 for p in src['packets']), default=1))
    for side in ('row_labels', 'column_labels'):
        src[side] = {key: value*a for key, value in src[side].items()}
    for packet in src['packets']:
        packet['symbol_pairs'] *= a
        packet['occupied_slots'] = [[slot*(L-1), edge] for slot, edge in packet['occupied_slots']]
    result = PacketLayout(parent.content_digest, a, u, canonical(src), base.strategy)
    if not audit_layout(parent, result)['group_load_bound_met']:
        raise ValueError('general-coordinate layout violates actual port load')
    return result

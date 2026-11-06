"""Bounded, parent-bound input layouts for finite transfer experiments."""

from pathlib import Path

from .model import PacketLayout, Refusal, canonical, decode
from .shrinking_layout import audit_vertex_shrinking_layout, construct_vertex_shrinking_layout


def load_transfer_layout(parent, path, *, groups, budget):
    if type(groups) is not int or not 64 <= groups <= 1024:
        raise ValueError('finite group count must be an integer in 64..1024')
    if path is None:
        return construct_vertex_shrinking_layout(parent, groups=groups, budget=budget)
    path = Path(path)
    if path.stat().st_size > budget.policy.max_certificate_bytes:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'transfer layout byte cap')
    raw = path.read_bytes()
    budget.tick(len(raw))
    value = decode(raw, cap=budget.policy.max_certificate_bytes)
    if (type(value) is not dict or set(value) != {'schema', 'parent_digest', 'source'}
            or value['schema'] != 'VERITAS_R98_TRANSFER_LAYOUT_V1'
            or value['parent_digest'] != parent.content_digest
            or type(value['source']) is not dict or value['source'].get('r') != groups
            or type(value['source'].get('r')) is not int):
        raise ValueError('transfer layout fields, parent or group count mismatch')
    layout = PacketLayout(parent.content_digest, 1, 1, canonical(value['source']), 'balanced_vertices')
    audit_vertex_shrinking_layout(parent, layout)
    return layout

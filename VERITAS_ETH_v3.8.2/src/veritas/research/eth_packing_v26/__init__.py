"""Finite exact implementation of the packet-packing lemma, isolated from v2.5.

Paper object: `lem:tensor-packets` in `app:tensor` of the pinned OpenAI
preprint (vendored in `paper/`). The historical "D.3" label is an alias; see
`docs/OPENAI_PAPER_CONFORMANCE.md`.
"""
from .constructor import construct_d3_packing, d3_preconditions
from .checker import verify_d3_packing
from .geometry_audit import audit_sparse_packet_geometry
from .implicit import (ImplicitPacking, audit_d3_child_wire_loads,
                       check_implicit_packing, construct_implicit_packing,
                       construct_preconditioned_d3_packing,
                       implicit_mode_source, implicit_sparse_mode_source,
                       real_packet_slots)

__all__ = [
    'construct_d3_packing', 'verify_d3_packing', 'd3_preconditions',
    'ImplicitPacking', 'construct_implicit_packing', 'check_implicit_packing',
    'implicit_mode_source', 'implicit_sparse_mode_source', 'real_packet_slots',
    'audit_d3_child_wire_loads', 'audit_sparse_packet_geometry',
    'construct_preconditioned_d3_packing',
]

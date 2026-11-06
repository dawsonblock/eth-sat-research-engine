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
from .streaming import (D3PreconditionsNotMet, StreamingPackingBuild,
                        construct_active_call_streaming_packing,
                        construct_streaming_d3_packing,
                        estimated_streaming_work)
from .streaming_check import verify_streaming_d3_certificate
from .complete_bipartite import (
    construct_complete_bipartite_active_call,
    complete_bipartite_packet_address,
)
from .complete_bipartite_check import verify_complete_bipartite_certificate
from .packet_bijection import (DirectedClassOffset, PacketAddress,
                               decode_packet_address, edge_occurrence_address,
                               edge_occurrence_at_address, encode_class_offset)
from .packet_bijection_check import (verify_global_packet_bijection,
                                     verify_implicit_packing_packet_addresses)
from .global_packet_address import (
    GlobalPacketIndex, audit_global_packet_index, build_global_packet_index,
    decode_packet_address as decode_global_packet_address,
)

__all__ = [
    'construct_d3_packing', 'verify_d3_packing', 'd3_preconditions',
    'ImplicitPacking', 'construct_implicit_packing', 'check_implicit_packing',
    'implicit_mode_source', 'implicit_sparse_mode_source', 'real_packet_slots',
    'audit_d3_child_wire_loads', 'audit_sparse_packet_geometry',
    'construct_preconditioned_d3_packing',
    'StreamingPackingBuild', 'D3PreconditionsNotMet',
    'construct_streaming_d3_packing', 'estimated_streaming_work',
    'construct_active_call_streaming_packing',
    'verify_streaming_d3_certificate',
    'construct_complete_bipartite_active_call',
    'complete_bipartite_packet_address',
    'verify_complete_bipartite_certificate',
    'PacketAddress', 'DirectedClassOffset', 'encode_class_offset',
    'decode_packet_address', 'edge_occurrence_address',
    'edge_occurrence_at_address', 'verify_global_packet_bijection',
    'verify_implicit_packing_packet_addresses',
    'GlobalPacketIndex', 'build_global_packet_index',
    'decode_global_packet_address', 'audit_global_packet_index',
]

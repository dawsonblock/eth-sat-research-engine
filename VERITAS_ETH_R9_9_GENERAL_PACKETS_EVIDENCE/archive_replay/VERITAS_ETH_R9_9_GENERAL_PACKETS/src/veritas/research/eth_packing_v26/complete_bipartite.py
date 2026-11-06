"""Compressed source-compatible D.3 packing for complete bipartite families.

This is a specialized deterministic construction for K_{N,N}, with paper
parameters r=64 and a=1. This is a packing-lemma example; a=1 cannot occur
in the paper's active schedule. It materializes neither the N**2 edges nor their
packet list. Every edge's label and packet address is defined by arithmetic
on its two endpoint indices; the independent checker validates the closed
form certificate. This does not replace the generic streaming constructor or
prove the universal packing lemma.
"""
from __future__ import annotations


COMPLETE_BIPARTITE_SCHEMA = "VERITAS_ETH_D3_KNN_COMPRESSED_V2"
PAPER_RADIX = 64
LABEL_DIMENSION = 1
LABEL_COUNT = PAPER_RADIX ** LABEL_DIMENSION
PAIR_CLASS_COUNT = LABEL_COUNT ** 2
PACKET_WIDTH = 1 << LABEL_DIMENSION
MIN_ELIGIBLE_N = 2 * PAIR_CLASS_COUNT**2
MAX_PARAMETER_BITS = 256


def complete_bipartite_packet_address(n: int, row: int, column: int) -> dict:
    """Return the implicit D.3 packet address of edge ``(row, column)``."""
    if type(n) is not int or n <= 0 or n % LABEL_COUNT:
        raise ValueError("N must be a positive multiple of the 64-symbol label count")
    if type(row) is not int or type(column) is not int or not (0 <= row < n and 0 <= column < n):
        raise ValueError("edge endpoint is outside K_{N,N}")
    s = n // LABEL_COUNT
    row_symbol, column_symbol = row % LABEL_COUNT, column % LABEL_COUNT
    row_rank, column_rank = row // LABEL_COUNT, column // LABEL_COUNT
    class_rank = row_rank * s + column_rank
    if row_symbol == column_symbol:
        return {
            "unordered_pair": [row_symbol, row_symbol],
            "packet_index": class_rank // PACKET_WIDTH,
            "slot": class_rank % PACKET_WIDTH,
        }
    return {
        "unordered_pair": [min(row_symbol, column_symbol),
                           max(row_symbol, column_symbol)],
        "packet_index": class_rank,
        "slot": 0 if row_symbol < column_symbol else 1,
    }


def construct_complete_bipartite_active_call(n: int) -> dict:
    """Build a compressed packing-lemma certificate for ``K_{N,N}``.

    Eligibility is checked before the certificate is constructed. The output
    describes all edges through closed-form label and packet-address rules;
    it is not an expanded edge-by-edge transcript.
    """
    if type(n) is not int or n <= 0:
        raise ValueError("N must be a positive integer")
    if n.bit_length() > MAX_PARAMETER_BITS:
        return {
            "status": "INCONCLUSIVE_RESOURCE_LIMIT",
            "certificate": None,
            "reason": "N exceeds the explicit 256-bit parameter cap",
        }

    m = n * n
    delta = n
    d_arr = PAIR_CLASS_COUNT
    l = PACKET_WIDTH
    conditions = {
        "M_ge_2_D_squared_delta": m >= 2 * d_arr * d_arr * delta,
        "M_ge_LD": m >= l * d_arr,
        "2L_le_delta": 2 * l <= delta,
    }
    if n % LABEL_COUNT != 0 or not all(conditions.values()):
        return {
            "status": "INCONCLUSIVE_D3_PRECONDITIONS",
            "certificate": None,
            "parameters": {"N": n, "M": m, "delta": delta,
                           "r": PAPER_RADIX, "a": LABEL_DIMENSION,
                           "D_arr": d_arr, "L": l},
            "preconditions": conditions,
            "reason": "requires N divisible by 64 and all pinned active-call inequalities",
        }

    per_symbol = n // LABEL_COUNT
    directed_class_load = per_symbol * per_symbol
    padded_height = ((directed_class_load + l - 1) // l) * l
    port_load = per_symbol * n
    child_wire_bound = 2 * port_load
    certificate = {
        "schema": COMPLETE_BIPARTITE_SCHEMA,
        "claim": "COMPRESSED_COMPLETE_BIPARTITE_PACKING_LEMMA_INSTANCE",
        "paper_labels": ["lem:tensor-packets", "eq:tensor-packing-conditions"],
        "graph": {
            "kind": "complete_bipartite_K_N_N",
            "N": n,
            "edge_set": "{(i,j): 0<=i<N and 0<=j<N}",
            "canonical_edge_order": "row-major (i*N+j)",
        },
        "parameters": {
            "r": PAPER_RADIX,
            "a": LABEL_DIMENSION,
            "label_count": LABEL_COUNT,
            "D_arr": d_arr,
            "L": l,
            "M": m,
            "Delta": delta,
        },
        "preconditions": conditions,
        "labeling": {
            "row_rule": "row_index_mod_64",
            "column_rule": "column_index_mod_64",
            "vertices_per_symbol_per_side": per_symbol,
            "deterministic": True,
            "construction_scope": "closed-form structured family construction",
        },
        "packetization": {
            "directed_class_count": d_arr,
            "real_edges_per_directed_class": directed_class_load,
            "uniform_padded_height": padded_height,
            "padding_per_directed_class": padded_height - directed_class_load,
            "packet_width": l,
            "packet_count": d_arr * padded_height // l,
            "address_rule": "complete_bipartite_packet_address(N,row,column)",
            "equal_symbol_pair": "packet=class_rank//2; slot=class_rank%2",
            "unequal_symbol_pair": "packet=class_rank; slot=0 for ascending orientation else 1",
            "class_rank": "(row_index//64)*(N//64)+(column_index//64)",
        },
        "loads": {
            "row_ports_per_symbol": port_load,
            "column_ports_per_symbol": port_load,
            "row_bound_3M_over_64": port_load <= 3 * m // PAPER_RADIX,
            "column_bound_3M_over_64": port_load <= 3 * m // PAPER_RADIX,
            "child_wire_count": child_wire_bound,
            "child_wire_strictly_below_M_over_8": 8 * child_wire_bound < m,
        },
        "resource_ledger": {
            "edges_materialized": False,
            "labels_materialized": False,
            "packet_slots_materialized": False,
            "certificate_size_independent_of_M": True,
            "bigint_parameter_cap_bits": MAX_PARAMETER_BITS,
            "runtime_is_full_generic_D3_complexity_bound": False,
        },
        "qualification": {
            "paper_fixed_radix": True,
            "numeric_active_call_eligible": False,
            "this_structured_family_packing_certified": False,
            "universal_packing_lemma_proven": False,
            "theorem_mode_enabled": False,
            "parent_child_contraction_proven": False,
        },
    }
    return {"status": "READY_FOR_INDEPENDENT_CHECK", "certificate": certificate}

"""Independent verifier for compressed K_{N,N} D.3 certificates.

This checker deliberately does not import the constructor or its address
function. It re-derives all constants and bounds, and for small N also checks
every edge address for injectivity and completeness. Large-N certificates use
the checked quotient/remainder address schema; the universal proof of that
schema is a separate Lean obligation.
"""
from __future__ import annotations


SCHEMA = "VERITAS_ETH_D3_KNN_COMPRESSED_V2"
LEGACY_SCHEMA = "VERITAS_ETH_D3_KNN_COMPRESSED_V1"
EXHAUSTIVE_EDGE_LIMIT = 100_000


def _address_independent(n: int, i: int, j: int) -> tuple:
    q = 64
    width = 2
    per_symbol = n // q
    row_symbol, col_symbol = i % q, j % q
    local_rank = (i // q) * per_symbol + (j // q)
    if row_symbol == col_symbol:
        return (row_symbol, row_symbol), local_rank // width, local_rank % width
    return ((min(row_symbol, col_symbol), max(row_symbol, col_symbol)),
            local_rank, int(row_symbol > col_symbol))


def verify_complete_bipartite_certificate(certificate) -> dict:
    """Check a finite, compressed fixed-radix packing-lemma instance.

    No edge or packet list is materialized. A valid result certifies the
    declared K_{N,N} family's numeric D.3 conditions, label histogram, class
    loads, padding arithmetic, and address schema. It does not certify the
    generic packing lemma or recursive tensor theorem.
    """
    try:
        if not isinstance(certificate, dict):
            raise ValueError("certificate must be an object")
        required = {
            "schema", "claim", "paper_labels", "graph", "parameters",
            "preconditions", "labeling", "packetization", "loads",
            "resource_ledger", "qualification",
        }
        if set(certificate) != required:
            raise ValueError("certificate fields differ from schema")
        if certificate["schema"] not in (SCHEMA, LEGACY_SCHEMA):
            raise ValueError("incorrect certificate schema")
        expected_claim = ("COMPRESSED_COMPLETE_BIPARTITE_D3_ACTIVE_CALL"
                          if certificate["schema"] == LEGACY_SCHEMA else
                          "COMPRESSED_COMPLETE_BIPARTITE_PACKING_LEMMA_INSTANCE")
        if certificate["claim"] != expected_claim:
            raise ValueError("incorrect certificate schema or claim")
        if certificate["paper_labels"] != [
                "lem:tensor-packets", "eq:tensor-packing-conditions"]:
            raise ValueError("source contract labels mismatch")

        graph = certificate["graph"]
        if not isinstance(graph, dict) or set(graph) != {
                "kind", "N", "edge_set", "canonical_edge_order"}:
            raise ValueError("malformed graph declaration")
        n = graph["N"]
        if (graph["kind"] != "complete_bipartite_K_N_N" or
                graph["edge_set"] != "{(i,j): 0<=i<N and 0<=j<N}" or
                graph["canonical_edge_order"] != "row-major (i*N+j)" or
                type(n) is not int or n < 1 or n % 64):
            raise ValueError("unsupported or malformed K_N,N input declaration")

        params = certificate["parameters"]
        if not isinstance(params, dict) or set(params) != {
                "r", "a", "label_count", "D_arr", "L", "M", "Delta"}:
            raise ValueError("malformed parameter object")
        q, d_arr, width = 64, 64**2, 2
        m, delta, per_symbol = n*n, n, n//q
        expected_params = {
            "r": q, "a": 1, "label_count": q, "D_arr": d_arr,
            "L": width, "M": m, "Delta": delta,
        }
        if params != expected_params:
            raise ValueError("derived paper parameters are incorrect")

        expected_preconditions = {
            "M_ge_2_D_squared_delta": m >= 2*d_arr*d_arr*delta,
            "M_ge_LD": m >= width*d_arr,
            "2L_le_delta": 2*width <= delta,
        }
        if certificate["preconditions"] != expected_preconditions or \
                not all(expected_preconditions.values()):
            raise ValueError("active-call hypotheses fail or are misstated")

        labeling = certificate["labeling"]
        if labeling != {
                "row_rule": "row_index_mod_64",
                "column_rule": "column_index_mod_64",
                "vertices_per_symbol_per_side": per_symbol,
                "deterministic": True,
                "construction_scope": "closed-form structured family construction",
        }:
            raise ValueError("label construction is not the declared periodic rule")

        real_class_load = per_symbol*per_symbol
        padded_height = ((real_class_load + width - 1)//width)*width
        packet_count = d_arr*padded_height//width
        packet = certificate["packetization"]
        expected_packet = {
            "directed_class_count": d_arr,
            "real_edges_per_directed_class": real_class_load,
            "uniform_padded_height": padded_height,
            "padding_per_directed_class": padded_height-real_class_load,
            "packet_width": width,
            "packet_count": packet_count,
            "address_rule": "complete_bipartite_packet_address(N,row,column)",
            "equal_symbol_pair": "packet=class_rank//2; slot=class_rank%2",
            "unequal_symbol_pair": "packet=class_rank; slot=0 for ascending orientation else 1",
            "class_rank": "(row_index//64)*(N//64)+(column_index//64)",
        }
        if packet != expected_packet:
            raise ValueError("packet counts, padding, or address rule mismatch")
        if padded_height % width or padded_height < real_class_load:
            raise ValueError("invalid uniform padding")
        if packet_count*width != d_arr*padded_height:
            raise ValueError("packet-slot accounting mismatch")
        if d_arr*padded_height > 3*m:
            raise ValueError("source packet-count bound fails")

        port_load = per_symbol*n
        child_size = 2*port_load
        loads = certificate["loads"]
        expected_loads = {
            "row_ports_per_symbol": port_load,
            "column_ports_per_symbol": port_load,
            "row_bound_3M_over_64": 64*port_load <= 3*m,
            "column_bound_3M_over_64": 64*port_load <= 3*m,
            "child_wire_count": child_size,
            "child_wire_strictly_below_M_over_8": 8*child_size < m,
        }
        if loads != expected_loads or not all((
                loads["row_bound_3M_over_64"],
                loads["column_bound_3M_over_64"],
                loads["child_wire_strictly_below_M_over_8"])):
            raise ValueError("port-load or child-shrink arithmetic mismatch")

        resource = certificate["resource_ledger"]
        if resource != {
                "edges_materialized": False,
                "labels_materialized": False,
                "packet_slots_materialized": False,
                "certificate_size_independent_of_M": True,
                "bigint_parameter_cap_bits": 256,
                "runtime_is_full_generic_D3_complexity_bound": False,
        }:
            raise ValueError("resource or representation claims mismatch")
        qualification = certificate["qualification"]
        if qualification != {
                "paper_fixed_radix": True,
                "numeric_active_call_eligible": certificate["schema"] == LEGACY_SCHEMA,
                "this_structured_family_packing_certified": False,
                "universal_packing_lemma_proven": False,
                "theorem_mode_enabled": False,
                "parent_child_contraction_proven": False,
        }:
            raise ValueError("qualification flags must remain fail-closed")

        exhaustive = m <= EXHAUSTIVE_EDGE_LIMIT
        if exhaustive:
            occupied = set()
            for i in range(n):
                for j in range(n):
                    address = _address_independent(n, i, j)
                    if address in occupied:
                        raise ValueError("duplicate edge packet address")
                    occupied.add(address)
            if len(occupied) != m:
                raise ValueError("edge address enumeration is incomplete")

        return {
            "valid": True,
            "status": "COMPRESSED_FIXED_RADIX_D3_INSTANCE_REPLAYED",
            "graph_kind": "K_N_N",
            "N_per_side": n,
            "M": m,
            "paper_radix_64": True,
            "numeric_active_call_eligible": False,
            "packing_lemma_inequalities_checked": True,
            "source_schedule_checked": False,
            "legacy_active_call_claim_discarded": certificate["schema"] == LEGACY_SCHEMA,
            "label_histogram_and_loads": "FORMULA_REPLAYED",
            "packet_address_coverage": "EXHAUSTIVE" if exhaustive else "QUOTIENT_REMAINDER_FORMULA",
            "edges_enumerated": m if exhaustive else 0,
            "directed_classes_checked_arithmetically": d_arr,
            "port_load_per_symbol": port_load,
            "child_wire_count": child_size,
            "child_wire_strictly_below_M_over_8": True,
            "universal_packing_lemma_proven": False,
            "parent_child_contraction_proven": False,
            "theorem_mode_enabled": False,
        }
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return {"valid": False, "status": "INVALID_COMPRESSED_D3_CERTIFICATE",
                "reason": str(exc), "universal_packing_lemma_proven": False,
                "theorem_mode_enabled": False}

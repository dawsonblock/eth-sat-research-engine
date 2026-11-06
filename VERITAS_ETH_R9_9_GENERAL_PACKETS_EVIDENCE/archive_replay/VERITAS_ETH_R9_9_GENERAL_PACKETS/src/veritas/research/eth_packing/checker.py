"""Independent packet certificate validator; recomputes every structural fact.

The verifier accepts JSON-like dictionaries, disregards all claimed scores
and rejects duplicate/missing wires, altered endpoints, malformed padding,
wrong orientation, and violations of the stated global inequalities.
"""
from __future__ import annotations
from collections import Counter


def check_packing(certificate: dict, *, require_bounds: bool = False) -> dict:
    try:
        r, a, L = (certificate[k] for k in ("r", "a", "L"))
        if type(r) is not int or type(a) is not int or not (2 <= r <= 64 and 1 <= a <= 5 and L == 1 << a):
            raise ValueError("invalid radix/packet size")
        edges = certificate["edges"]
        if not isinstance(edges, list) or len(edges) > 4096:
            raise ValueError("invalid edge list")
        if any(not isinstance(edge, list) or len(edge)!=2 or
               any(type(v) is not int or v < 0 for v in edge) for edge in edges):
            raise ValueError("invalid edge endpoint")
        vertices = set(v for edge in edges for v in edge)
        raw_labels = certificate["labels"]
        if set(raw_labels) != {str(v) for v in vertices}:
            raise ValueError("label vertex set mismatch")
        labels = {}
        for v in vertices:
            label = raw_labels[str(v)]
            if not isinstance(label,list) or len(label) != a or any(type(k) is not int or not 0 <= k < r for k in label):
                raise ValueError("invalid vertex labels")
            labels[v] = label
        packets = certificate["packets"]
        if not isinstance(packets,list) or len(packets) > 4096:
            raise ValueError("invalid packets")
        seen = Counter()
        for packet in packets:
            if not isinstance(packet,dict) or set(packet) != {"symbol_pairs", "slots"}:
                raise ValueError("invalid packet fields")
            pairs, slots = packet["symbol_pairs"], packet["slots"]
            if not isinstance(pairs,list) or len(pairs) != a or not isinstance(slots,list) or len(slots)!=L:
                raise ValueError("invalid packet dimensions")
            for pair in pairs:
                if not isinstance(pair,list) or len(pair)!=2 or any(type(x) is not int for x in pair) or not 0 <= pair[0] <= pair[1] < r:
                    raise ValueError("invalid symbol pair")
            for slot, eid in enumerate(slots):
                if eid is None:
                    continue
                if type(eid) is not int or not 0 <= eid < len(edges):
                    raise ValueError("invalid edge reference")
                seen[eid] += 1
                left, right = edges[eid]
                for d, pair in enumerate(pairs):
                    sym0, sym1 = pair
                    bit = (slot >> d) & 1
                    expected = (sym1, sym0) if bit else (sym0, sym1)
                    if (labels[left][d], labels[right][d]) != expected:
                        raise ValueError("slot alignment violation")
        if any(seen[eid] != 1 for eid in range(len(edges))):
            raise ValueError("missing or repeated real wire")
        M = len(edges)
        loads = []
        for side in (0,1):
            for d in range(a):
                c = Counter(labels[edge[side]][d] for edge in edges)
                loads.extend(c.values())
        max_load = max(loads, default=0)
        packets_ok = len(packets) * L <= 3*M if M else len(packets)==0
        balance_ok = max_load*r <= 3*M if M else True
        result = {"valid_structure": True, "all_bounds_satisfied": packets_ok and balance_ok,
                  "packet_count_bound": packets_ok, "symbol_load_bound": balance_ok,
                  "packet_count": len(packets), "edge_count": M,
                  "max_symbol_load": max_load, "max_allowed_packet_count": (3*M)//L,
                  "symbol_load_numerator": max_load*r, "symbol_load_denominator": r,
                  "status": "CERTIFIED_FINITE_INVARIANTS" if packets_ok and balance_ok else "STRUCTURE_ONLY_BOUNDS_NOT_MET"}
        if require_bounds and not result["all_bounds_satisfied"]:
            raise ValueError("numeric manuscript-form bounds not satisfied")
        return result
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        return {"valid_structure": False, "all_bounds_satisfied": False,
                "status": "INVALID_CERTIFICATE", "reason": str(exc)}

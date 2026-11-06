"""Check complete padded packet counts and real ports separately."""

from collections import Counter
from veritas.research.eth_packing_v26.implicit import check_implicit_mode_source


def check_packing(source, edges):
    if not 0 < len(edges) <= 8 or [list(e) for e in edges] != source["edges"]:
        raise ValueError("packing is for a different or unsupported parent")
    # Check the canonical conditional-expectation record as well as the loads below.
    canonical = check_implicit_mode_source(source, max_work=1_000_000)
    if canonical.get("valid") is not True:
        raise ValueError("invalid packing source")
    M, L, a, r, H = source["M"], source["L"], source["a"], source["r"], source["H_pad"]
    if M != len(edges) or L != 1 << a or not 1 <= a <= 3 or not 2 <= r <= 64 or H % L:
        raise ValueError("packing dimensions")
    rows, cols = source["row_labels"], source["column_labels"]
    loads = [[Counter(), Counter()] for _ in range(a)]
    seen = set()
    addresses = set()
    for packet in source["packets"]:
        pairs = tuple(map(tuple, packet["symbol_pairs"]))
        for slot, edge in packet["occupied_slots"]:
            if not 0 <= edge < M or not 0 <= slot < L or edge in seen:
                raise ValueError("duplicate edge or invalid slot")
            seen.add(edge)
            address = (pairs, packet["index"], slot)
            if address in addresses:
                raise ValueError("packet collision")
            addresses.add(address)
            u, v = edges[edge]
            for j, (x, y) in enumerate(zip(rows[str(u)], cols[str(v)])):
                if pairs[j] != (min(x, y), max(x, y)) or (
                    x != y and ((slot >> j) & 1) != int(x > y)
                ):
                    raise ValueError("incorrect orientation")
                loads[j][0][x] += 1
                loads[j][1][y] += 1
    if seen != set(range(M)):
        raise ValueError("incomplete edge occurrence set")
    N = r ** (2 * a) * H // L
    coords = [
        {
            "row": [side[0][g] for g in range(r)],
            "column": [side[1][g] for g in range(r)],
        }
        for side in loads
    ]
    sides_ok = all(r * max(row) <= 3 * M for coord in coords for row in coord.values())
    return {
        "padded_packets": N,
        "occupied_packets": len(source["packets"]),
        "actual_loads": coords,
        "packet_bound_met": N * L <= 3 * M,
        "both_port_bounds_met": sides_ok,
        "universal_packing_proved": False,
    }

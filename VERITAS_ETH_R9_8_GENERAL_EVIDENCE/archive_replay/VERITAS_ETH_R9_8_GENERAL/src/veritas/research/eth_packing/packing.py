"""Exact finite slot-class packet arrangement and transparent certificates.

A packet of size L=2^a has slots with fixed unordered symbol pairs at
all coordinates, with the slot bits controlling endpoint orientation.
Repeated-equal symbols are allowed on both sides; their slot bit is
arbitrary, so we select slot 0 in that coordinate.

This constructor is *not* the full D.3 conditional-expectation proof.
It does establish concrete structural invariants; the independent checker
verifies the stronger packet-count and symbol-load bounds when satisfied.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict
from .labels import assign_endpoint_labels


class PackingLimit(ValueError):
    pass


def _edge_slot(labels, u, v, a):
    pair_key = []
    slot = 0
    for d in range(a):
        left, right = labels[u][d], labels[v][d]
        pair_key.append((min(left, right), max(left, right)))
        if left > right:
            slot |= (1 << d)
    return tuple(pair_key), slot


def construct_packing(edges, *, r=4, a=2, labels=None, max_edges=4096,
                      enforce_bounds=False):
    edges = tuple(tuple(edge) for edge in edges)
    if len(edges) > max_edges:
        raise PackingLimit("edge budget exceeded")
    if not 1 <= a <= 5 or not 2 <= r <= 64:
        raise PackingLimit("1<=a<=5 and 2<=r<=64 required")
    for pair in edges:
        if len(pair) != 2 or any(not isinstance(v, int) or v < 0 for v in pair):
            raise ValueError("edges must be pairs of nonnegative vertex IDs")
    if labels is None:
        labels = assign_endpoint_labels(edges, r=r, a=a)
    else:
        labels = {int(k):tuple(v) for k,v in labels.items()}
    bucket = defaultdict(lambda: defaultdict(list))
    for eid, (u, v) in enumerate(edges):
        key, slot = _edge_slot(labels, u, v, a)
        bucket[key][slot].append(eid)
    packets = []
    for key in sorted(bucket):
        number = max(map(len, bucket[key].values()))
        for i in range(number):
            slots = [bucket[key][slot][i] if i < len(bucket[key].get(slot, [])) else None
                     for slot in range(1 << a)]
            packets.append({"symbol_pairs": [list(p) for p in key], "slots": slots})
    certificate = {"version": 1, "r": r, "a": a, "L": 1 << a,
                   "edges": [list(edge) for edge in edges],
                   "labels": {str(v): list(lab) for v,lab in labels.items()},
                   "packets": packets, "claim": "FINITE_PACKET_INVARIANTS_ONLY"}
    from .checker import check_packing
    report = check_packing(certificate)
    certificate["verification"] = report
    if enforce_bounds and not report["all_bounds_satisfied"]:
        raise PackingLimit("constructed packet schedule does not meet the required numerical bounds")
    return certificate

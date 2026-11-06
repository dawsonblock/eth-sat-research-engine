# Exact finite pair-packet optimization: v2.0.0

## Objective

Given a legal tensor network whose every edge appears in exactly two factor
ports, partition the `n` edge indices into consecutive packets of size two,
with one possible final singleton. A factor contributes `binom(c,2)` for
`c` of its incident indices in any packet. Minimize the lexicographic tuple
`(sum of collision pairs, peak factor incidence in a packet)`.

## Equivalence to min-weight perfect matching

Let `w(a,b)` be the number of factors incident to both distinct wires
`a,b`. A packet of two wires contributes exactly `w(a,b)` collisions. Thus
for even `n`, any legal packet partition is a perfect matching of the
complete graph weighted by `w`, and vice versa; minimizing the sum of the
matching weights is exactly minimizing the collision score. For odd `n`,
add a dummy vertex connected to each real wire with weight zero. Any
perfect matching then has one dummy pair; its real partner becomes the
singleton packet. The costs still coincide exactly.

For pair packets, the peak incidence is 2 if *any* pair has positive weight,
and otherwise 1 if `n>0` (0 if `n=0`). Hence its value is determined by
the minimum primary objective, proving lexicographic optimality as well.

NetworkX's minimum-weight maximum-cardinality matching is used as a finite
polynomial-time Blossom implementation. Input is a complete graph with
`n` (or `n+1`) nodes, requiring O(n^2) graph memory. The requested timeout
is not a hard deadline on the third-party matching function.

## Verification boundaries

- `matching_checker.verify_matching_evidence` independently replays the
  permutation, collision score, peak incidence and lower bound directly
  from original factor incidences. It also rejects mismatched metadata.
- For <=16 wires, the independent exhaustive subset DP re-computes the
  finite global optimum, when it completes within its explicit budget.
- For larger networks the algorithm is globally optimal by its matching
  reduction and the contract of the external matching implementation, but
  **no independent cryptographic or mathematical certificate** is emitted.
- Wire permutation is a bijection preserving F(0), the undeformed tensor
  contraction, not necessarily preserving the deformed polynomial F(t).

## Implementation points

- `src/veritas/research/matching_packets.py`
- `src/veritas/research/matching_checker.py`
- API: `/v1/research/packet-schedule` with `optimizer: matching` and
  `packet_size: 2`; <=128 wires, <=12 wires for independent count cross-check.
- CLI: `--matching-packets --packet-size 2`
- Cauchy: `--cauchy-eliminate --optimize-packets --packet-optimizer matching`
- Browser: `Globally optimal pair packets via matching (v2.0)`
- Tests: `tests/test_v20_matching_packets.py`
- Differential validation: `scripts/validate_v20.py`

## What the improvement does not prove

The paper's D.3 quantitative collision-packing theorem is not reducible to
this particular wire pairing score. A global optimum of the surrogate need
not optimize the exact Cauchy deformation's arithmetic runtime, or the
number of its retained modes under weighted recursion. Generic exact SAT
counting remains exponential in the worst case in this codebase.

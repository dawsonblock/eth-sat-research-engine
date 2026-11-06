# v2.1 exact and bounded finite packet search

This module optimizes a **finite engineering surrogate** only. Nothing here
implements OpenAI's manuscript D.3 collision-packing theorem, D.4.4
recurrence, or a subexponential SAT/#SAT algorithm.

## The combinatorial objective

For a tensor network with wire set V and local factors F, partition V into
packets of k wires, except possibly a final partial packet of size n mod k.
For each packet P define:

- `c(P) = Σ_f choose(|ports(f) ∩ P|, 2)`
- `p(P) = max_f |ports(f) ∩ P|`

Minimize `(Σ_P c(P), max_P p(P))` lexicographically. Since each unordered
wire pair (u,v) contributes the number of factors containing both wires,
this is weighted k-set partitioning with nonnegative edge weights. The new
branch-and-bound implementation supports packet sizes 1,2,4,8 and at most
24 wires. It does not assume the finite objective predicts runtime.

## Sound lower bound

If the remaining r wires form complete k-packets, each vertex v must have
exactly k-1 packet-mates. Let `ℓ(v)` be the sum of the k-1 smallest pair
weights from v to the other remaining wires. Every actual completion has
cost at least `ceil(Σ_v ℓ(v) / 2)`, because each chosen within-packet pair
is counted at both endpoints. Together with nonnegative accumulated cost
this is an admissible branch-and-bound lower bound.

When there is a required final partial packet, the current implementation
retains the safe global lower bound zero if search stops early. It does not
imply the best candidate is near-optimal.

## Exactness versus bounded search

- Finished search: the canonical partition enumeration is complete, with
  safe bound-based pruning. This is an **internal algorithmic optimum**.
- Small finished search: an independent subset-DP oracle can also replay
  the optimal value (<=12 wires by default).
- Interrupted search: the returned schedule is **feasible**, and the claimed
  global lower bound is checkable; no optimum is claimed. The gap is an
  absolute difference in collision pairs, not a runtime approximation.
- The separate `bounded_partition_checker.py` independently replays all
  incidence collisions and the admissible lower bound. For larger cases it
  does not independently certify the completeness of the branch search.

Global caps apply to states, generated candidate blocks and wall time.
No solver-generated partial result can be relabeled as a verified optimum.

## Run

```bash
veritas-cli cnf examples/example.cnf --bounded-packets --packet-size 4 --max-packet-states 150000 --timeout 5
python scripts/validate_v21.py
python benchmarks/v21_packet_search.py
python -m pytest -q
```

API: `POST /v1/research/packet-schedule`, body:

```json
{"n":3,"clauses":[[1,2],[-1,3]],"optimizer":"bounded","packet_size":4,"cross_check":true}
```

## Research gaps

The OpenAI Lean scope document states a subexponential k-CNF counting
result. The finite collision objective used here is not the quantitative
packing condition of the manuscript, and no reduction from this finite
optimum to the claimed recurrence has been established.

Primary scope: https://github.com/openai/math/blob/main/lean/docs/378.md

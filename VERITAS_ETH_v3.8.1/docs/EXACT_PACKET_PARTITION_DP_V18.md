# v1.8 exact finite packet-partition optimizer

## Scope and theorem boundary

This is an **exact combinatorial optimizer for the v1.1 surrogate packet-incidence score**, not a reproduction of the quantitative packet-packing theorem in OpenAI's October 25 2026 ETH manuscript. It neither proves the manuscript's mode-count bounds nor establishes a subexponential SAT algorithm.

Source project: https://github.com/openai/math/tree/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026

Given a tensor network with `m` wires, each incident to exactly two factors, a packet size `L` in `{1,2,4,8}`, and a wire permutation `pi`, partition the permuted wire positions consecutively into blocks of size `L` (last possibly shorter). For factor `f` and packet `P`, let `c(f,P)` count wire incidences in the block. Define:

```
C(pi) = sum_f sum_P c(f,P)*(c(f,P)-1)//2
I(pi) = max_{f,P} c(f,P)
```

The optimizer minimizes `(C(pi), I(pi), pi)` lexicographically over all permutations. The first two coordinates are the mathematics of interest; the final coordinate is only a deterministic tie-break.

## Exact subset-DP recurrence

Let `B` be a set of unassigned wires, where `|B|` is divisible by `L`. Let `v` be the smallest wire in `B`, and let `Q` range over every size-`L` subset of `B` containing `v`. Let `(c(Q),i(Q))` be the collision score and maximum incidence for that packet. With `F(empty)=(0,0,())`, define

```
F(B) = lexicographic min_Q (
    c(Q) + F(B\Q).collisions,
    max(i(Q), F(B\Q).max_incidence),
    sorted(Q) + F(B\Q).wire_order
)
```

Every partition into equal full packets is represented, because packets are interchangeable and some packet contains `v`. The least-wire anchor eliminates redundant packet permutations, but not any packet **partition**. If `m % L != 0`, enumerate every possible final partial packet `R` of size `m % L`, solve `F(all\R)`, and append `sorted(R)`. All valid packet groupings appear in that search. Within each packet, sorted ascending wire order yields the lexicographically smallest equivalent permutation. Recomputing `collision_score` on the selected order independently checks the reported objective.

Because every full packet is examined and the finite recurrence has a terminating base case, the result is optimal *for this objective* provided the search completes. A deadline, state-cap or transition-cap violation raises `PacketPlanningLimit`; no partial optimum is returned.

## Limitations

- At most **16 tensor wires**; the exponential DP is not scalable.
- Optimizes *incidence collisions*, not the exact D.3/D.4.4 packing invariants.
- Does not guarantee lower intermediate tensor width, faster Cauchy elimination, or fewer modes in the paper's construction.
- Reordering preserves `F(0)` (original count) but can change the deformed polynomial `F(T)` for `T != 0`; the Cauchy oracle is evaluated using the **same permuted network**.
- `FINITE_OPTIMUM_DP_REPLAYED` denotes exact finite-search evidence, not a Lean proof or the manuscript theorem.

## Interfaces

```
veritas-cli cnf examples/example.cnf --optimal-packets --packet-size 2
veritas-cli cnf examples/example.cnf --cauchy-eliminate --optimize-packets --packet-optimizer exact_dp
python scripts/validate_v18.py
python benchmarks/v18_packets.py
```

POST `/v1/research/packet-schedule` with `{ "n": 4, "clauses": [[1,2],[-1,3]], "packet_size": 2, "optimizer": "exact_dp" }`. The original `"optimizer": "legacy"` behavior is retained by default. POST `/v1/research/cauchy-eliminate` accepts `"optimize_packets": true, "packet_optimizer": "exact_dp"` to use the new scheduler for the research jet calculations.

## Evidence and release gates

1. Enumerate **all** permutations independently for small networks and check both the score and the selected tie-break permutation.
2. Check the count-preserving relabeling invariant by comparing direct original contraction with an independently contracted relabeled network.
3. Compare the new exact optimizer against the legacy local-swap heuristic on 15-wire networks (cannot be worse under the objective).
4. Check modular Cauchy jets against the independent exhaustive shifted-kernel evaluator *after relabeling*.
5. Force resource caps to ensure they fail closed.

A fixed 12-wire factor network has legacy collision score `6` and the exact DP achieves `5`. This is a surrogate-score reduction and **not** a measured #SAT speedup.

# v1.9 — Scalable packet scheduling and independently checked finite lower bounds

## Exact mathematical object

Given a network of `n` Boolean wires and factors `f`, partition the wires into
consecutive packets of size `L∈{1,2,4,8}`. The final packet may be smaller.
Let `d(f,P)` count incidences of wires in packet `P` on factor `f`.
The surrogate objective is

```
C = Σ_f Σ_P choose(d(f,P), 2)
I = max_{f,P} d(f,P)
```

The scheduler minimizes the pair `(C,I)` lexicographically, approximately,
using a deterministic seeded multistart local search. As in v1.8, this **is not**
the manuscript's D.3 packet-packing condition, and minimizing `C` does not
necessarily accelerate exact SAT or Cauchy contraction.

## Global bound and proof

Let `p=ceil(n/L)` be the number of packets, and `d=|ports(f)|` be a factor's
degree. In any partition, writing `d=pq+r` for `0≤r<p`, convexity of
`choose(x,2)` gives

```
Σ_P choose(d(f,P),2) >= (p-r)*choose(q,2) + r*choose(q+1,2).
max_P d(f,P) >= ceil(d/p).
```

The sum of the per-factor pair bounds and maximum of per-factor peak bounds
are *global lower bounds* for all schedules. They may be unattainable together
because different factors share wires and the last packet may have less capacity.

For an actual schedule whose score `(C,I)` **equals both bounds**, the result
is globally optimal **for this surrogate score**, without exhaustive search.
If the bounds are not attained, `pair_gap=C-LB` quantifies an upper bound on
how far the optimum can be below the achieved pair score, *not* an achieved
optimality gap. We do not mislabel that schedule as optimal.

The standalone `packet_bound_checker.py` does not call the optimizer or the
original `collision_score`; it recomputes each factor's true incidence count
from the proposed permutation and derives the bound by independently placing
unit incidences into least-occupied hypothetical bins. Mutated bounds, scores,
or permutations are rejected. This is a checkable finite combinatorial
certificate, *not a formal Lean proof and not a certificate of ETH complexity*.

## Algorithm and resource limits

- Build the pair-coincidence weights from the network's factor incidences.
- Evaluate identity, a deterministic greedy grouping, and seeded restarts.
- Perform strictly improving cross-packet wire swaps, evaluating only their
  two affected packets before accepting a candidate.
- Maintain the incumbent whenever time or evaluation budgets expire; unlike
  exact search, bounded heuristic search may validly return a feasible,
  replay-verified schedule without having finished exploring.
- The finite search is capped at `256` wires by default, `25,000` candidate
  swaps, and a `5` second time budget. Explicit parameters permit a larger
  cap but may use O(n²) memory for co-incidence weights.
- For deterministic reproducibility, set `seed`, `restarts`, and
  `max_evaluations` explicitly. Results at very short wall-clock budgets can
  still depend on machine speed.

## Interfaces

```
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v19.py
python benchmarks/v19_packet_search.py

veritas-cli cnf examples/example.cnf --scalable-packets --packet-size 4 \
  --packet-search-evaluations 20000 --packet-search-restarts 4 \
  --packet-search-seed 1919
```

API: `POST /v1/research/packet-schedule` accepts
`{"n":4,"clauses":[[1,2],[-1,3]],"optimizer":"scalable", "packet_size":2}`.
For networks with more than 12 wires, specify `"cross_check":false` because
exhaustive original-count replay is infeasible; the independent incidence
bound checker still runs. The API caps scalable requests at 128 occurrences,
128 variables, 128 clauses and dense factor degree 12. High-occurrence
variables require COPY3 preprocessing outside this endpoint.

Cauchy polynomial elimination (`--cauchy-eliminate --optimize-packets
--packet-optimizer scalable`) accepts the new scheduler, subject to the
existing 12-wire Cauchy execution cap. The exact DP and legacy options remain.

## Explicit limitations

1. No manuscript D.3 packing theorem or quantitative asymptotic guarantee.
2. No manuscript D.4.4 weighted-mode runtime, nor a subexponential solver.
3. Search may be slower than doing nothing, particularly for small networks.
4. The lower bound may be weak, even when the returned schedule is actually
   optimal; lack of equality does not establish nonoptimality.
5. The planner is memory- and work-bounded in its own logic, not under an
   operating-system hard memory sandbox. Keep the server on loopback.
6. Reordering wires changes the deformed polynomial at nonzero interpolation
   parameters; compare a Cauchy oracle using the *same relabeled network*.

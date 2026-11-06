# VERITAS-ETH v1.7: exact elimination-order optimization

## Implemented

`src/veritas/research/optimal_order.py` finds a **globally optimal order for a
specified dense operation proxy** on factor graphs with at most 12 variables.
It does not solve #SAT faster in the worst case, does not certify real wall-clock
optimality, and does not reproduce OpenAI's ETH paper D.3/D.4.4 theorem.

For a graph `G` and an elimination order `pi`, eliminating vertex `v` fills in
all missing edges between `v`'s current neighbors. Define `d_pi(v)` as the
number of neighbors immediately before that elimination. The two supported
objectives are:

- `work`: minimize `sum_v 2**(d_pi(v)+1)`; tie-break on maximum `d_pi(v)`.
- `width`: minimize `max_v d_pi(v)`; among all orders with this globally
  minimum width, choose the least dense-work score.

These scores are deterministic planning proxies. Real running time also depends
on factor sparsity, table contents, integer bit length, Python overhead, and
model formulation.

## Exact dynamic program

A state `S` is the subset of vertices already eliminated. Eliminating the same
set `S` in any order produces the same filled graph on the remaining vertices:
`u,v` are adjacent after eliminating `S` iff there exists an original path from
`u` to `v` with all internal vertices in `S`. The implementation computes
filled neighbors by following original edges through vertices in `S`.

For work minimization:

```
C(V) = 0
C(S) = min_(v not in S) [2**(d_S(v)+1) + C(S union {v})]
```

For width minimization, a first subset DP finds the minimum achievable peak
width, and a second subset DP minimizes work **subject to that fixed width
limit**. This two-pass algorithm is necessary: blindly optimizing a single
lexicographic `(width, work)` value per suffix can lose feasible
minimum-width solutions with better total work.

At most `2**n` subset states are explored per DP pass, each considering at most
`n` choices. `n<=12` bounds the search space. Timeouts terminate with `UNKNOWN`
without reporting an incomplete optimum.

## Validation and evidence scope

The resulting plan is independently replayed through a separate mutable
filled-graph algorithm (`replay_order`), and its width is cross-checked against
an independently verified elimination-tree decomposition. The finite-subset
DP optimum is established by exhaustive state recurrence **for the given
primal graph and objective**, not by Lean, and is not a succinct mathematical
proof certificate. Tests independently enumerate **every permutation** of
small variable sets and verify the DP's work optimum and minimum width.

The `optimal_small` planner mode uses the **original CNF variable model**;
it does not claim global optimality over COPY3 and all alternative
representations. The local browser and API expose `optimal_small` separately
from the default fast-first heuristic. They never secretly switch to separator
DP when this mode is selected.

## Usage

```sh
python -m pip install -e '.[test]'
veritas-cli cnf examples/example.cnf --optimal-order-report --optimal-objective work
veritas-cli cnf examples/example.cnf --optimal-order-report --optimal-objective width
veritas-cli cnf examples/example.cnf --adaptive-contract --adaptive-portfolio optimal_small
python scripts/validate_v17.py
python benchmarks/v17_optimal_order.py
```

Endpoint for order only (never returns a satisfying-assignment count):

`POST /v1/research/optimal-order`

```json
{"n":4,"clauses":[[1,2],[-1,3],[3,4]],"objective":"work"}
```

Use `POST /v1/research/adaptive-contract` with
`"portfolio_mode":"optimal_small"` for exact counting under execution limits.

## Limitations and open research

* The ordering optimization itself is exponential in the number of variables;
  calling it on a large network is intentionally rejected.
* Plan optimization cost can dominate runtime on small instances. This mode is
  optional and not the default.
* The dense operation proxy does not account for sparse joins or arithmetic
  bit lengths. Numerical gains are instance-dependent.
* Resource budgets bound modeled operations and factor sizes, **not physical
  OS-level process memory**.
* The paper's specific collision-packing construction, quantitative
  valuation-weighted mode bounds and subexponential recursion remain absent.

# R9.12 exact elimination route and factorized support

This note covers three additions to R9.12: a bounded-width exact elimination
route, a route selector that classifies its results separately, and a
factorized representation of the existing mode support. None of them
implements, qualifies or supports the manuscript's source recursion. An
elimination result is not evidence for the source-recursive or any
subexponential bound.

## Why the recursive route refuses the 96-wire interaction fixture

`build_support` grows S_{r+1} = S_r ∪ {β+e_j : j ∈ I_r} over the nonconstant
affine rows, keeping only β with Σ w_j β_j < P, and refuses once the set
exceeds `Policy.max_tuples` (4096). Its size is bounded only by ∏(1+|I_r|).

On `scripts/experiment_r912_interaction.py` (32+32 vertices, 96 wires, every
vertex rank > 1 in each flattening) the root point at t=-1 folds to 96 modes.
Each of the 96 nonconstant rows touches exactly one mode, every row is its own
component, and P = 6656 is far above any reachable weight. The support is
therefore the entire cube {0,1}^96, of size 2^96. The bound ∏(1+|I_r|) is
attained. The run stops with `complete supported tuple cap` after about 4.36M
work units. No `max_tuples` or work allowance can make it finish, and none was
changed. `tests/test_r912_support_circuit.py` checks the 2^96 count exactly.

## Exact elimination (`parent_child_r912.elimination`)

Every wire is one Boolean variable and every vertex is one factor over its
ordered ports. Eliminating wire x replaces the factors f_1..f_k containing x by
g(y) = Σ_{x∈{0,1}} ∏_i f_i(x,y). Entries come from `evaluate_compiled` at
creation precision, exactly as in the four-edge leaf. All arithmetic stays in
(Z/2^P Z)[U]/(f(U))[V]/(V^ell). There is no floating point.

- `plan_order` is a greedy min-fill (default) or min-degree heuristic.
- `verify_order` independently replays the order symbolically. It checks that
  the order is a permutation of every wire. It recomputes each frontier, the
  width w (largest frontier, in wires), the largest table, the peak live
  table entries and the exact predicted work, Σ_steps 2^(|frontier|+1)·k plus
  input and final charges. These are compared with an `EliminationBudget`
  (`max_width`, `max_table_entries`, `max_live_entries`, `max_work`,
  `max_seconds`).
- `eliminate` repeats the replay and compares it with the certificate before
  it evaluates any entry. Afterwards it checks that the allocated peak entries
  and charged work equal the prediction. Work and time overruns raise
  `INCONCLUSIVE_RESOURCE_LIMIT`. Nothing partial is returned.

The cost is O(N·2^(w+1)) ring operations, which is exponential in the
verified width. The width is that of the heuristic order. It is not a
treewidth lower bound. Table budgets count ring elements, not bytes, and
no OS memory limit is enforced.

## Route selection (`parent_child_r912.routes`)

`contract_routed(parent, route=Route.AUTO|ELIMINATION|RECURSIVE, elimination_budget=..., **recursive)`:

- `RECURSIVE` calls the unchanged `parent_child_r910.engine.contract`.
- `ELIMINATION` runs only if the verified order fits the budget. Otherwise it
  returns `INCONCLUSIVE_ELIMINATION_BUDGET` with no result, before any
  allocation.
- `AUTO` uses elimination when the order fits. Otherwise it runs the
  recursive executor and records why elimination was refused.

Results carry `result_classification`. This is `EXACT_ELIMINATION` for the
elimination route and `FINITE_TAPERED_RECURSION` for the recursive route.
Elimination reports also record `recursive_route_used: false` and
`complexity_status: EXPONENTIAL_IN_VERIFIED_WIDTH`. Every report keeps
`source_qualified`, `theorem_mode_enabled`, `theorem_aligned`,
`source_recursive_bound_evidence` and `subexponential_bound_evidence` false.
The existing recursive entry points, CLI and replay checker are unchanged.

## Factorized support (`parent_child_r99.support_circuit`)

`SupportCircuit` represents the same set as `build_support`: the Boolean
support of G(X,z) = ∏_r (1 + Σ_{j∈I_r} X_j z^{w_j}) mod z^P. Rows with
identical incidence form one power node. Rows that share no mode split G
into components on disjoint coordinates. A layered decision diagram over
the components, whose state is the accumulated weight below P, joins them.
States merge by weight, but distinct exponent vectors stay distinct paths.
The count is the number of paths. `tuples(limit=...)` refuses above an
explicit expansion limit. Weights must be nonnegative integers. This is a
representation only and no executor uses it. A factorized representation
does not reduce the number of child calls that the recursive point sum makes.

## Evidence

The sweep over every `graph(32, offset)` fixture, offsets 2..31, is in
`VERITAS_ETH_R9_12_RING_OPTIMIZATION_EVIDENCE/exact_elimination/`
(`summary.json`). All 30 runs match the independent Python-integer
elimination reference. Verified widths range from 5 to 19. The default
offset 5 has width 17, the same as the reference frontier, and takes about
4.4 s. For offsets 7, 13 and 23 the reference's own min-degree frontier
exceeded 22, so the reference was rerun with the planned order. It still
recomputes every scope and uses only Python integers, and the order changes
only its cost. The failed attempts are kept beside the successful runs.

```
PYTHONPATH=src python scripts/experiment_r912_interaction.py --output-dir /abs/external/run
PYTHONPATH=src python -m pytest tests/test_r912_exact_elimination.py \
  tests/test_r912_support_circuit.py tests/test_r912_negative_properties.py
```

## Not established

Certified child-sum aggregation, the 484→44→4 multilevel run, the source
schedule and packing proof (u_d, a_d, L, r, D, M ≥ 2D²Δ), and cost and space
bounds all remain open. Nothing here bears on them.

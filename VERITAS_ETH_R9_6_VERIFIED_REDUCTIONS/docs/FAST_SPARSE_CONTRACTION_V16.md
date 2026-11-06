# VERITAS-ETH v1.6 exact contraction optimization

## Implementation

- `research/indexed_contract.py`: compiles factor bit projections and performs exact dense Boolean elimination without allocating an assignment dictionary for every row. Projection scratch space is capped, with slower on-demand extraction for large buckets. Uses the same elimination ordering and exact-arithmetic semantics as v1.5.
- `research/sparse_contract.py`: exact sparse hash join over nonzero factor assignments, followed by sum-out. It is especially appropriate for COPY/equality-heavy factors, and can be slower for dense clause factors. Nonzero entries, join work, and wall-clock time are bounded. The reported `peak_table_entries` in this mode counts nonzero rows, unlike dense modes. The initial input factor tables are still constructed densely and must fit the input factor cap.
- `research/contraction_planner.py`: `portfolio_mode=auto` first tests a single original-variable min-degree plan and accepts it if its dense cost fits the resource limits. If not, falls back to the six-plan v1.5 portfolio. `portfolio_mode=thorough` forces all candidate representations/heuristics. Auto does not guarantee the globally cheapest order.
- `research/boundary_dp.py`: leaf problems test a quick order before computing more candidates and execute using selected arithmetic backend.

## Example

```bash
veritas-cli cnf examples/example.cnf --adaptive-contract --adaptive-portfolio auto --adaptive-execution indexed
veritas-cli cnf examples/example.cnf --adaptive-contract --adaptive-portfolio thorough --adaptive-execution sparse
python scripts/validate_v16.py
python benchmarks/v16_adaptive.py
```

API `POST /v1/research/adaptive-contract` accepts `portfolio_mode` (`auto` or `thorough`) and `execution_mode` (`indexed`, `legacy`, `sparse`). All three are exact for completed supported calculations; modular output remains a residue, not necessarily the full count. If a work, entry or time limit is exceeded, no count is reported.

## Scope and limitations

These are conventional treewidth-sensitive exact operations with exponential worst-case time and potentially exponential memory. No implementation of D.3 or D.4.4 collision packing, weighted low-rank mode-count proof, or the paper's subexponential complexity theorem is claimed. This release does not provide OS-enforced RAM isolation, external certified tree decomposition, or formal verified correctness of the Python runtime. Comparative timings are specific to measured cases and include planning; do not claim general speedups without representative repeatable workloads.

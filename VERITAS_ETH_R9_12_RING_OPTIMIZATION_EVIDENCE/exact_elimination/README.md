# 96-wire interaction sweep: exact elimination route

Produced by `scripts/experiment_r912_interaction.py` from
`VERITAS_ETH_R9_12_RING_OPTIMIZATION`. `offset_05` is the default fixture and
also contains the unchanged recursive run. That run is
`INCONCLUSIVE_RESOURCE_LIMIT` with `complete supported tuple cap` and has no
result. The other offsets ran with `--skip-recursive`.

Each `offset_NN/` directory contains `input.json`, the independent integer
`reference.json` and the routed `elimination.json`. `summary.json` collects
them; regenerate it with `python3 summarize.py`.

`failed_reference_min_degree_offset_{07,13,23}` keep the first attempts. In
those, the reference oracle's own min-degree frontier exceeded its cap of 22.
The successful reruns pass `--reference-order planned_min_fill`. The order
affects only the oracle's cost: it still recomputes every scope in Python
integers.

These are finite exact contraction results classified `EXACT_ELIMINATION`.
They are not evidence for the source recursion or any subexponential bound.

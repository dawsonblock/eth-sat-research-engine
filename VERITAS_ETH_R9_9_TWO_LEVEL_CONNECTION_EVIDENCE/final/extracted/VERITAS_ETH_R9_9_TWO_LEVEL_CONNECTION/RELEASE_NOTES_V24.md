# VERITAS-ETH v2.4.0 — Exact batch posterior inference

Cumulative source upgrade from v2.3.0. No previous algorithms intentionally removed.

- Adds exact rational all-variable posterior marginals using reverse differentiation of the proof-checked component counting DAG, rather than a separate full count per variable.
- Adds independent marginal proof replay with formula+weights+count-DAG binding.
- Correct handling of deterministic priors, zero-weight branches, contradictory evidence, and declared unused variables.
- Integrates API, CLI, local browser, seeded exhaustive validation, and a matched-result benchmark.
- Corrects the API health version metadata (which was stale at 2.1.0) and the legacy tests that pinned the obsolete value.
- Explicitly unchanged: paper-specific D.3 collision packing and D.4.4 subexponential algorithm are NOT implemented.

See `docs/EXACT_POSTERIOR_MARGINALS_V24.md`, `validation/validation_v24.json`, and `validation/benchmark_v24.json`.

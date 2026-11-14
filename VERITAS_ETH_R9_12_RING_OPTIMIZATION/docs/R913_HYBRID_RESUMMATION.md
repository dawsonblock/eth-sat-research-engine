# R9.13 hybrid packet resummation (experimental)

This note records the method decision table from external benchmarking
(`scripts/bench_sat_methods.py`) and the integration path through
`parent_child_r912.fixture_bridge`. Nothing here qualifies manuscript-active
recursion, an ETH theorem, or a subexponential bound. All `source_qualified` and
`subexponential_bound_evidence` flags remain **false**.

## Verified identity (bounded fixtures)

For a **packet** recipe at fixed Boolean row bits, row factors
`F_r(z) = c_r + Σ_j a_{rj} z_j` multiply to `P(z)`. At mode weights `s`,

```text
Σ_β A_β Π_j s_j^{β_j}  =  Π_r (c_r + Σ_j a_{rj} s_j)
```

`parent_child_r913.algebraic_resummation` checks this by explicit monomial
expansion versus direct substitution. Production `evaluate_compiled` returns the
single exponent coefficient at the recipe target (plus source column powers),
not the full substitution sum; tests cross-check that coefficient against the
expanded oracle.

## Support + precision truncation

`parent_child_r913.support_resummation` applies the same substitution identity
after filtering monomials to the R9.12 affine-row support at a chosen precision
cutoff (`SupportCircuit`). When the cutoff keeps every multilinear monomial,
supported enumeration agrees with full substitution and with component-hybrid
multiplication on disjoint row components. When the cutoff is tight, full
substitution can differ from supported enumeration; the supported sum is then the
reference for “one mode per row” semantics, not an automatic substitute for
`P(s)` on the full polynomial.

| Route | What it does | When to use | Limitation |
| ----- | ------------ | ----------- | ---------- |
| **Original-wire elimination** (`Route.ELIMINATION`) | Exact bounded-width Boolean elimination on wire scopes; preflight budgets fail closed | Production baseline on fixtures where width fits `EliminationBudget` | Exponential in verified width; heuristic order only |
| **Full packet substitution** (`substitution_resummation`) | `Π_r (c_r + Σ_j a_{rj} s_j)` without enumerating β | Cross-check / small packet children at a jet point | Does not replace wire elimination on large parents |
| **Support-filtered resummation** (`compare_support_aware_resummation`) | Truncated weighted DP with `SupportCircuit` weights | Same jet point under affine-row support + cutoff | Multilinear `expand` path is diagnostic only, not the supported aggregate |
| **Truncated weighted DP** (`truncated_weighted_resummation`) | `Q(t)=∏_r(c_r+Σ a_{rj} s_j t^{w_j})` mod `t^P`; sum degrees `<P` | **Primary** precision-truncated aggregate | Does not extract a single recipe exponent; not full recursion |
| **Mode-graph elimination width** (`dependency_analyzer`) | Min-fill order on mode incidence; **no** factor evaluation | Preflight / planning next to wire width | Width is heuristic, not treewidth; NP-hard optimum not sought |
| **Recursive tapered contraction** (`Route.TAPERED` / explicit support) | Factorized support circuit + child construction | Research path when support stays under caps | 96-wire interaction: full `2^96` support — refuses at tuple cap |

External benchmarks concluded: at width 17 on the 96-wire interaction fixture,
mode-side elimination metadata matches wire elimination cost class; **standalone
child-factor execution** is not the next research target. Next work is
**algebraic packet resummation** (`P(s)` substitution) plus adaptive exact
contraction at bounded interpolation points (see `fixture_bridge` + jet
recovery).

## Single interpolation point integration

`compiled_child_packet_at_jet_point` builds one constructor packet at a jet
recovery point. Tests run `compare_support_aware_resummation` and
`polynomial_target_value` / `production_packet_value` on that compiled entry.
If parent precision is too high for local expansion budgets, resummation raises
or returns resource refusal — fail closed, do not claim a partial theorem.

## Optional comparison wrapper

For a quick A/B at one point:

```bash
PYTHONPATH=src python scripts/bench_sat_methods.py --smoke
```

Use `--cases wire_elimination,packet_resummation` to subset. Raising
`--elimination-max-width` only affects cases that call the elimination route;
the optional `--interaction-wires 192` label runs **metadata preflight only** on
a larger circulant sketch (no full cube enumeration).

## Qualification strings

| Key | Value |
| --- | ----- |
| `qualification` | `experimental_support_filter_only` (support path) or `heuristic_elimination_width_not_treewidth` (mode analyzer) |
| `source_qualified` | false |
| `subexponential_bound_evidence` | false |

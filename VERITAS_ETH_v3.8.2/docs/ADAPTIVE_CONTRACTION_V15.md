# VERITAS-ETH v1.5 — Exact adaptive contraction

## What is actually implemented

`original_cnf_model` maps original variables to Boolean factor scopes. It removes tautological clauses, deduplicates literals in the same clause, handles contradictions and empty clauses, and retains declared-but-unused Boolean variables as free binary factors. `copy3_model` instead uses v1.4's count-preserving occurrence-wire equality chains. Either representation can be contracted exactly.

`graph_decomposition` builds the *primal graph*: an edge joins variables co-occurring in a factor. This is not the paper's collision-packing graph. The planner runs three deterministic heuristics: minimum degree (fewest active neighbors), minimum fill (fewest new edges on elimination), and weighted minimum fill (new-edge count times neighbor count). The third is an engineering cost proxy, not an optimality proof. The elimination-tree decomposition is checked for graph edge coverage, forest validity and running intersection.

`contraction_planner` estimates peak dense factor size as `2^induced_width` and sums estimated assignment evaluations. It evaluates up to six candidate plans: three orderings for each of the original-CNF and COPY3 representations. The planner selects the least estimated dense work among feasible plans, preferring original CNF on ties. Estimates are not guaranteed runtimes.

`boundary_dp` detects disconnected subproblems and optionally conditions on small separating vertex sets. It computes exact counts of each conditioned component, multiplies component counts and sums separator assignments. Canonical exact factor tables allow memoizing identical subproblems. Index slicing on a high-degree variable is available when an elimination plan exceeds the table/work budget. Slicing may **increase** total arithmetic and is capped by `max_slices`.

The adaptive executor enforces per-input and intermediate table budgets, a shared leaf-evaluation budget, a call bound, a cache-entry limit, a deadline and a slice-depth bound. If these fail the result is `UNKNOWN` and no partial count is reported. Exact integers or residues modulo `2^precision_bits` are supported. Modular residues must **not** be presented as full counts unless precision suffices.

## Mathematical correctness

For any factors of Boolean variables `V`, the count is `Z = sum_{x in {0,1}^V} product_f f(x_scope(f))`. Variable elimination uses distributivity. Given a separator `S` whose deletion disconnects into components `C_i`, conditioning the factors on each `s in {0,1}^S` gives `Z = sum_s product_i Z_{C_i}(s)` (times factors depending only on `S`). Each original variable is summed exactly once. Restricting a factor to `s` creates its truth table over remaining variables with first port as low bit. All arithmetic is exact integer or modular arithmetic.

**These are conventional treewidth-dependent algorithms with exponential worst-case complexity.** The code does not reproduce the manuscript's D.3 collision-packing schedule, D.4.4 bounded weighted-mode recurrence or asymptotic `2^{o(n)}` result. Nor is the method a Lean formalized proof. Reproducible differential tests corroborate individual finite cases but cannot certify general correctness or source-level theorem equivalence.

## API and CLI

`POST /v1/research/adaptive-contract`, JSON:

```json
{"n": 4, "clauses": [[1,2],[-2,3],[3,4]], "timeout_s": 10,
 "enable_separators": true, "max_separator": 2, "max_slices": 3,
 "include_copy3": true, "max_table_entries": 65536,
 "max_work_assignments": 2000000, "cross_check": true}
```

`status` is `EXACT_COUNT`, `COUNT_RESIDUE`, or `UNKNOWN`; `count` is a **decimal string** and exists only on successful completion. The API independently checks against exhaustive #SAT for inputs with <=10 variables and <=128 clauses when `cross_check` is enabled, but larger calculations are explicitly marked *not independently checked*. A SHA-256 audit identifier records the input and response.

Command-line example:

```sh
veritas-cli cnf examples/example.cnf --adaptive-contract --timeout 10
```

Additional flags: `--adaptive-no-copy3`, `--adaptive-no-separators`, `--adaptive-table-cap 4096`, `--adaptive-max-slices 2`, `--max-work-assignments 100000`, and `--precision-bits 16`.

## Performance and trust requirements

Compare identical formulas with v1.4 using `python benchmarks/v15_adaptive.py` and run `python scripts/validate_v15.py` plus `pytest`. One-run wall times are observations, not general claims. Monitor total planning cost, peak table entries, exact operation counts, actual process memory and cache behavior before drawing conclusions about larger inputs. Optional third-party decomposition planners and sparse/decision-diagram arithmetic remain future work; they are **not** shipped as implemented features.

# Residual-function equivalence and symbolic state compression

**Status:** research direction tied to universal SAT / R9.13 — not a proved
subexponential #SAT algorithm. `universal_speedup_claimed` remains **false**.

## Core idea

Define partial assignments `a`, `b` equivalent when residual problems match:

```text
a ~ b   iff   R(a) = R(b)
```

Count with multiplicities:

```text
#F = Σ_R   mult(R) · #SAT(R)
```

instead of enumerating `2^n` full assignments. XOR / GF(2) Gaussian elimination
is the linear prototype: exponentially many assignments, one rank computation.

## What VERITAS already has

| Mechanism | Role relative to this idea |
| --------- | ----------------------------- |
| `solvers/count_dag.py` | Canonical residual `State`, memoized `#SAT(R)` with verifiable DAG |
| `sat_phase_c_reduction.py` | **Factor** independent components (`PRODUCT` invariant) |
| `sat_residual_equivalence.py` | Explicit **multiplicity buckets** after variable-prefix branching |
| `parent_child_r913/truncated_weighted_resummation.py` | Algebraic **merge** on bounded row products (problem A) |
| Separator / coefficient elimination (R9.13 plan) | **Eliminate** modes toward one coefficient, not full state space |

The gap is not “no merging” but **merging partial assignments into equivalence
classes before exponential blow-up**, with proved bounds on `|{R}|` for a class
of formulas — still open for arbitrary 3-CNF.

## Proposed engine (five ops)

1. **Canonicalize** — `residual_state_key` / count_dag normalization.
2. **Merge** — multiplicity accumulation (`count_by_residual_equivalence`).
3. **Factor** — primal components + tensor product (`Phase C`).
4. **Eliminate** — R9.13 coefficient DP, XOR/GF(2) gadget, finite contraction.
5. **Verify** — exhaustive cross-check, count_dag certificate, independent oracle.

## R9.13 junction (three parallel tracks)

1. **Residual equivalence classes** — extend prefix/DPLL search to bucket by `R`;
   measure `distinct_residual_classes` vs `2^n` on seeded suites.
2. **Algebraic coefficient compression** — keep separating weighted aggregate (A)
   from specified coefficient (B); hunt merges that preserve **B** exactly.
3. **Recursive decomposition + merge** — parent–child ledger; prove when child
   residuals repeat across branches.

## Central test metric

On each instance record:

- `n`, `distinct_residual_classes`, `full_assignment_branches`
- `compression_ratio_branches_over_classes`
- Wall time and ledger `W_new` vs direct

Adversarial goal: families where `|{R}|` stays ~`2^Ω(n)` despite canonicalization.

## Toy anchor

`F = (x ∨ z) ∧ (y ∨ z)` — three of four `(x,y)` prefixes share the same residual;
count `3·#SAT(z fragment) + 1·#SAT(true)` without eight leaf enumerations.
See `tests/test_sat_residual_equivalence.py`.

## Universal pipeline integration (PR #6)

| Hook | Behavior |
| ---- | -------- |
| Count mode | `reduction.residual_compression` probe on every run (`probe_residual_compression`) |
| Phase C child | After `count_dag`, optional `residual_equivalence` engine (fail-closed if no oracle agreement) |
| Ledger | Step `residual_compression_probe` with class count as `w_transform` proxy |
| Micro-bench | `xyz_residual_coupled` fixture; suite fields `max_residual_compression_ratio` |

No change to `universal_speedup_claimed` (remains **false**).

### Micro-suite generators (CI, seeded)

`sat_micro_generators.py` adds **coupled** (path/triangle chains) and **adversarial**
(dense random, tight triangle cliques) families with `n ≤ 10`. Each universal
count run and micro-benchmark case records:

- `distinct_residual_classes`
- `compression_ratio_branches_over_classes` (branch-order dependent)
- `compression_vs_2n` ≈ `2^n / distinct_residual_classes` when `n ≤ 20`

Benchmark-only `probe_branch_orders_benchmark` tries three fixed orders (default,
odd-first, reversed) and reports `best_compression_ratio_branches_over_classes`
in micro-benchmark JSON **without** changing production default order.

Phase C count children try **`residual_equivalence` before `count_dag`** when oracle
agreement holds; `child_engine_telemetry` logs wins vs adaptive/exhaustive fallback.

Component-local **pure literal** elimination (`enable_component_safe_pure_literals`)
defaults off globally. When enabled, a variable is forced only if every incident
clause is a **unit clause** on that variable within a single primal component
(naive multi-literal pure literals break #SAT — e.g. `(x ∨ y)` with x only positive).

### Correctness gates (code)

- `count_by_residual_equivalence` returns `EXACT_COUNT` only when
  `count_computed == exhaustive_count(cnf)`; otherwise `INCONCLUSIVE_INVARIANT_FAILURE`
  and `count=None` (fail-closed child engine).
- `proved_in_repo` on count invariants is **always false** in universal JSON; partition
  validity is reported separately (`partition_certificate_valid`).

## References

- `docs/R913_COEFFICIENT_EXTRACTION_RESEARCH.md`
- `docs/UNIVERSAL_SAT_SPEEDUP_PLAN.md` (§2 work ledger)
- `src/veritas/research/sat_residual_equivalence.py`

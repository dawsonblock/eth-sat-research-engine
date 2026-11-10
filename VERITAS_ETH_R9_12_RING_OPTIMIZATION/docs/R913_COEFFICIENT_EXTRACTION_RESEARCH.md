# R9.13: structure-aware exact coefficient extraction (research plan)

This document records the **mathematical target** for R9.13 and separates it from
the truncated aggregate DP already implemented. Nothing here qualifies manuscript
recursion, ETH, or subexponential SAT unless separately proved with explicit
assumptions. All `source_qualified` and `subexponential_bound_evidence` flags
remain **false**.

## Two different problems

Row product

```text
P(z) = ∏_r (c_r + Σ_j a_{rj} z_j)
```

| Problem | Quantity | Typical use in VERITAS | R9.13 status |
| ------- | -------- | ---------------------- | ------------ |
| **A. Weighted truncated aggregate** | Σ_{β: Σ w_j β_j < P} A_β ∏_j s_j^{β_j} | Support-bounded sums, planning | **`truncated_weighted_resummation`** (proved row-wise DP on bounded fixtures) |
| **B. Specified coefficient** | A_β for one exponent β (× source column powers) | **`evaluate_compiled`** packet path | **`target_coefficient_by_separator_elimination`** (+ sources) on bounded graphs; full expansion reference when ≤18 modes |

**Do not** treat a fast answer to **A** as acceleration of **B**.

Example: P(z₁,z₂)=(1+z₁)(1+z₂), s=(1,1), β=(1,1):

| Method | Value |
| ------ | ----- |
| Coefficient A_{(1,1)} | **1** (production target) |
| Truncated aggregate, P=2 | **3** |
| Full substitution P(s) | **4** |

## Complexity barrier (informal)

Extracting a general coefficient in multilinear products encodes permanent-type
counting; exact extraction for unrestricted integer inputs is not expected to be
polynomial-time. Improvements must come from **restricted structure** (separator
width, bounded exponents, sparse incidence), not from the substitution identity
alone.

The ETH manuscript claim is a separate, unproved benchmark; this engineering path
does not assume it.

## Research steps (priority order)

### Step 1 — Exact preservation specification

Define and prove (or refuse) equalities along the full pipeline:

```text
Original problem value  =  Reconstructed parent value
```

Separate obligations for:

1. Supported weighted sum (problem **A**).
2. Specified packet coefficient (problem **B**).
3. Parent→child contraction.
4. Precision lift / modular reconstruction.
5. Final SAT decision (including modular false negatives).

Module: `parent_child_r913.research_spec` (schemas only; no theorems).

### Step 2 — One-dimensional truncated DP (problem **A**)

Prove row induction for

```text
D_R[d] = [t^d] ∏_r (c_r + Σ_j a_{rj} s_j t^{w_j})   (mod t^P)
```

Implemented in `truncated_weighted_resummation.py`; validated vs explicit β-oracle
on bounded integers and jet ring on packet fixtures.

### Step 3 — Separator-based coefficient extraction (problem **B**) — **central**

Implemented prototype: mode-graph variable elimination with β-pruned row
polynomial joins (`coefficient_extraction.target_coefficient_by_separator_elimination`).
Telemetry includes `max_monomial_table`, `join_count`, and elimination width from the
same min-fill planner used for wire elimination (not a treewidth certificate).

Track only exponent information required at separators when eliminating modes
from the row factor graph. Compare to full expansion on small instances.

Measure:

- Active boundary modes.
- Max required exponent per mode at separator.
- Intermediate table size (states × jet cost).

Relates to bucket elimination / treewidth-style counting; width **w** implies
O(2^w) Boolean boundary tables for separator states—**not** treewidth certificates
until proved.

Prototype module: `coefficient_extraction.py` (`estimate_extraction_state`, reference
extractors).

### Step 4 — Two-level recursive children

After a correct **B** on one jet point, compress through constructor children with
source columns and precision; compare two active levels to independent exact
replay (future milestone).

### Step 5 — Honest cost bounds

Report T(n) in terms of separator width w(n), state size q(n), precision P, and
jet work—**instance evidence** (e.g. width 17 on 96-wire circulant) is not a
uniform family theorem.

## Engineering baseline

Keep **original-wire elimination** (`Route.ELIMINATION`) as correctness and
performance fallback. R9.13 experiments must report **largest intermediate exact
state**, not only “vectors avoided.”

## Milestones

1. Correct end-to-end **96-wire child** computation under explicit budgets:
   `interaction_coefficient_harness.interaction_coefficient_end_to_end` (circulant
   32+32 / offset 5, jet point 1) reports parent wire elimination (width 17) and
   child separator `A_β` vs independent row reference without `2^96` expansion.
   Bench: ``interaction_96_e2e``. Remaining: two-level recursive child vs same oracle.
2. **192-wire** metadata + independent-row separator (`coefficient_extract_192`,
   `mode_width_192`); wire timing via ``bench_sat_methods.py --full``
   (``wire_elimination_192``). Child jet e2e at 192 modes awaits valid separated
   layout beyond the 32+32 probe. Budget refusal: ``elimination_budget_refusal``
   (width 17 vs ``max_width=16``).
3. Separator coefficient extractor matching expansion on n≤12 mode graphs before
   claiming solver-level benefit.

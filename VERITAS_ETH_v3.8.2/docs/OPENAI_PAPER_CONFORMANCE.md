# Conformance to the pinned OpenAI preprint

The finite reference in `src/veritas/research/` implements a bounded
version of the tensor-contraction appendix of *The Exponential Time
Hypothesis is False* (OpenAI, 25 October 2026). The paper's LaTeX source is
vendored in [`paper/`](../paper/README.md), and
`tests/test_openai_paper_conformance.py` asserts that every parameter the
code computes equals the paper's closed form.

This page is the index. It records, for each build component, the paper
object it corresponds to, and what the code does and does not establish.

## 1. Naming

The paper has no "Appendix D". The build historically used that label. The
aliases are:

| Build label | Paper object |
|---|---|
| "Appendix D" | `app:tensor`, *Proof of the contraction theorem* (`paper/quantitative-contraction.tex`) |
| "D.3 packing lemma" | `lem:tensor-packets`, *Packing into packets* (l. 114–171) |
| "D.3 numeric preconditions" / "D.6" | `eq:tensor-packing-conditions` (l. 106–109) |
| "D.4.4 recursion" | `subsec:tensor-children`, *The child networks and their descriptions* (l. 484–555) |
| "manuscript schedule" | `eq:tensor-parameters` (l. 87–91) plus the thresholds at l. 80–84 |
| "tapered Hermite" | `lem:tapered-hermite`, *Tapered Hermite recovery* (l. 250–269) |
| "mode expansion" | `eq:tensor-mode-expansion` (l. 418–425) and `subsec:tensor-modes` |

New code and new documentation should cite the paper label. The "D.x"
aliases are kept only so existing filenames (`APPENDIX_D_*.md`) and
docstrings remain findable.

## 2. Parameter table

All formulas are from `quantitative-contraction.tex`; `λ = ⌈log₂ s⌉`.

| Quantity | Paper | Code | Test |
|---|---|---|---|
| Leaf threshold | `H = ⌈s/⌊√λ⌋⌉` (l. 81) | `appendix_d_schedule.schedule_preflight` → `leaf_threshold` | `test_lambda_leaf_and_degree_match_the_paper` |
| Degree bound | `Δ = ⌈s^{9/10}⌉` (l. 83) | `_degree_limit` | same, plus `test_degree_limit_of_the_big_size_is_the_analytic_value` |
| Radix | `r = 64` (l. 82) | `r=64` in `eth_packing_v26`, `eth_modes_v27` | `test_d3_preconditions_are_the_paper_inequalities` |
| Radix constant | `ε = 1/(128·1024)` (l. 82) | `131072` in `schedule_preflight` | `test_schedule_u_and_a_match_the_paper` |
| Depth parameter | `u_d = ⌊ελ/2^d⌋` | `u = (λ//131072) >> d` | same |
| Packet exponent | `a_d = 2Σ_{j≤d}u_j`, `a₋₁=0` | `a = 2*Σ (base >> j)` | same |
| Packet size | `L = 2^a` | `L = 1 << a` | same |
| Class count | `D_arr = r^{2a}` | `r**(2*a)` | same |
| Packing hypotheses | `M ≥ 2D_arr²Δ`, `M ≥ LD_arr`, `2L ≤ Δ` | `d3_preconditions` | `test_d3_preconditions_are_the_paper_inequalities` |
| Packet bound | `≤ 3M/L` packets | `check_implicit_packing` → `packing_count_bound` | `test_packing_count_and_port_bounds_follow_the_paper_formulas` |
| Port bound | `≤ 3M/r` real ports per symbol | `max_side_symbol_load` | same |
| Child bound | `6M/r = 3M/32 < M/8` (l. 525–527) | `audit_d3_child_wire_loads` | `test_child_wire_bound_holds_when_the_packing_hypotheses_hold`, `test_child_bound_definitions_for_the_theorem_radix` |
| Interpolation scale | `α = 2^{a+1}` (l. 180) | `TaperedPlan.alpha` | `test_tapered_plan_matches_lemma_tapered_hermite` |
| Cauchy degree | `M(2L−1)` (l. 202) | `TaperedPlan.degree_bound` | same |
| Hermite multiplicity | `h = ⌈3M/u⌉`, `q_t = h·max(0,u−i)` | `make_tapered_plan` | same |
| Node precision | `p_t = p + 8hD_t + 8M(a+1)`, `D_t = L/2^i` | `TaperedPlan.nodes[*].precision_bits` | same |
| Mode weight | `w_Z = b+1`, `b+1 < p_t` | `point_modes.make_point_modes` | `test_mode_multiplicity_and_budget_are_the_paper_inequalities` |
| Mode multiplicity | `(3M/L)2^{i+1} = 6M/D` | `mode_denominator = L >> i` | same |
| Mode budget | `Σ_Z w_Z β_Z < p_t` | `structural_tuples` | same |
| Root precision | `P_0 = n+1`, `ℓ = 1` (reduction l. 86–88) | `recover_boolean_count`, `describe_integer_network` | `test_count_recovery_uses_paper_precision_and_unused_variables` |

### 2b. Shared linear summaries (`sec:counting`, `sec:construction`)

| Quantity | Paper | Code | Test |
|---|---|---|---|
| Radix, points, degree | `r = ⌊√λ/ν²⌋`, `Q = ⌊λ/(128ν)⌋`, `R = (β+3)⌈√λ⌉` (`eq:parameter-QR`) | `parameters.theorem_parameters_from_lambda` | `test_theorem_parameters_follow_the_paper_formulas` |
| Auxiliary constants | `τ = 1/(rλ)`, `ε = 1/(br²λ)`, `D = r^{2Q}` | same | same |
| Interval | `A₀ = ⌊Qp − (R−1)/2⌋`, `I = {A₀..A₀+R−1}` | same | same |
| Balance | `2(b+w)D² ≤ M`, `2Qr² ≤ n` | `FormParameters.check` | `test_parameter_schedule_matches_lemma_incidence_parameters` |
| Label set | `B = ([r]^Q)²` | `auxiliary.AuxiliaryLayout` | `test_auxiliary_structural_checks` |
| Swap matrix | `M₀ = V₀f_I(W₀)`, `W₀ = ½Σ(I−Π_s)` | `auxiliary` (Walsh transform) | `test_paper_remark_row_is_reproduced_exactly` |
| Row degree | `deg P_u ≤ R−1`, `P_u(0) = δ_u` | `AuxiliaryLayout.row_polynomial` | same |
| Support bound | `M₀[u,y] ≠ 0 ⇒ |E_{u,y}| ≤ R−1` | `check_support_bound` | same |
| Measurements | `c_B ≤ D·Pr[W ∉ I]` | `measurement_matrix` | `test_measurement_rows_are_the_binomial_tail` |
| Correction | `φ_{u,y}(T) = Π_{s∈E}(1 − T/s)` | `_phi_minus_one` | `test_paper_remark_row_is_reproduced_exactly` |
| Truncation | `q = ⌊d_H/Q⌋`, `J = q+1` | `FormParameters.q`, `.J` | `test_parameter_summary_reports_the_truncation` |
| Separation | `Z_E = Σ_y Π_g Σ_g(y)` | `separation.separation_sum` | `test_separation_matches_the_direct_sum` |
| Boolean differences | `eq:boolean-differences` | `taylor.enumerate_restriction_pairs` | `test_boolean_differences_identity_on_random_polynomials` |
| Taylor data | `eq:full-taylor-sum` | `taylor.taylor_series` | `test_taylor_series_matches_direct_evaluation` |
| Design | `def:layout` (5 items) | `layout.verify_layout` | `test_layout_replays_the_design` |
| Count | `H(0) = Z` | `count.count_instance` | `test_count_matches_brute_force` |

## 3. Component map

| Code | Paper |
|---|---|
| `eth_packing_v26/implicit.py` — `construct_implicit_packing`, `check_implicit_packing` | `lem:tensor-packets`. Conditional-expectation labelling, padded classes, packet slots. The implicit form keeps only nonempty classes; the explicit form materialises the padded array. |
| `eth_packing_v26/expectation.py` — `assign_full_d3_labels` | The proof of `lem:tensor-packets` (l. 131–147): exact conditional expectation by enumerating edge pairs. The incremental score update is an implementation optimisation of the same quantity. |
| `eth_packing_v26/implicit.py` — `audit_d3_child_wire_loads` | The port bound in `lem:tensor-packets`(3) and the deduction at l. 525–527. |
| `eth_interpolation/shifted_cauchy.py`, `eth_interpolation/cauchy_product.py` | `eq:tensor-cauchy` and `lem:tensor-integrality`. `shift_cauchy_entry` is the integral `W(t+αz)`; `cauchy_point_value` evaluates it at a residue. |
| `eth_interpolation/source_hermite.py` | `lem:tapered-hermite`, `eq:tensor-hermite-origin`: bounded full-node source functional, `h`, `q_t` and `p_t`; the finite recursor uses this path. The older `tapered_hermite.py` retains its separately checked prefix functional. Neither implementation establishes the general precision or complexity proof. |
| `eth_recursive_contraction_v39/point_modes.py` | `subsec:tensor-modes`: tiles `y = y₀ + 2^{i+1}j`, the geometric expansion `eq:tensor-mode-expansion`, mode weights and `column_terms`. |
| `eth_recursive_contraction_v39/structural_tuples.py`, `eth_modes_v27/enumeration.py` | `eq:tensor-mode-budget` and the enumeration remark at l. 476–482. |
| `eth_recursive_contraction_v39/point_children.py`, `lazy_children.py` | `subsec:tensor-children`: one child per group, packet vertices with retained ports, coefficient extraction, source-mode substitution. |
| `eth_recursive_contraction_v39/described_network.py` | The description/creation-precision discipline at l. 544–555 and l. 57–71. |
| `eth_recursive_contraction_v39/zero_wire.py` | l. 505–508: empty products equal one; a source tile with no real column contributes one at exponent zero. |
| `eth_arithmetic/extension_ring.py`, `jets.py` | `subsec:tensor-arithmetic`: `O = Z_(2)[U]/(f)`, `A = O[V]/(V^ℓ)`, `A_p = A/(2^p)`, coordinatewise precision. |
| `eth_arithmetic/boolean_count.py` | Reduction l. 90–93: `0 ≤ #F ≤ 2^n` and the residue modulo `2^{n+1}`. |
| `tapered_v4/` | The whole recursive driver: packing, modes, child construction, interpolation, recovery, depth-first traversal. |
| `appendix_d_schedule.py` | `eq:tensor-parameters`, `H`, `Δ`, and the induction invariants at l. 92–112. |

## 4. What the code does not establish

The paper proves Theorem `thm:tensor-contraction` for all sufficiently large
`s`, with a threshold depending only on the fixed constants, and derives
Theorem `thm:main` from it. The code is a **finite** reference:

- Every routine is capped (`M ≤ 32` in the tapered plan, `L ≤ 8` in the
  point-mode engine, precision and work budgets, tuple caps). The caps are
  far below `s^{1/1000}` at theorem scale.
- `r = 64` is implemented and checked, but the packing hypotheses
  `M ≥ 2D_arr²Δ` are unsatisfiable at the sizes the reference can reach, so
  the reference never exercises the theorem's parameter regime. The
  conformance tests therefore check the *formulas* and the *conditional*
  implication, not an instance of the theorem's hypotheses at scale.
- Nothing here proves uniform applicability of `lem:tensor-packets`, the
  precision bound `p_t = O_C(MD_t/u)`, the `O_C(log λ)` depth bound, or the
  total-work estimate. Those are paper proofs, not code results.
- `run_tapered_finite` and `contract_recursive` report finite-instance
  status only. Every certificate carries `universal_theorem_proven: false`
  and `subexponential_runtime_proven: false`.

The tests in `tests/test_openai_paper_conformance.py` check that the code
computes the paper's numbers. They are not a verification of the paper's
proof, and passing them does not upgrade any finite result.

## 5. Paper sections that are outside this build

The build now covers two halves of the paper:

* `app:tensor` (the contraction engine) -- `eth_recursive_contraction_v39`,
  `tapered_v4`, `eth_packing_v26`, `eth_interpolation`.
* `sec:counting` and `sec:construction` (the polynomial construction) --
  `eth_counting_v39`, documented in
  [`LINEAR_SUMMARIES_V39.md`](LINEAR_SUMMARIES_V39.md).

Still absent:

| Paper object | Status here |
|---|---|
| `thm:main` (main theorem) | Not claimed. The build has no subexponential-time result. |
| `subsec:sharp-fixed-density` -- the CNF-to-network encoding (clause vertices, equality chains, edge subdivision) | `source_cnf.source_cnf_network` normalizes clauses, constructs trivalent equality trees and subdivides every edge. `source_cnf_check` independently checks finite graph structure; count agreement is tested separately. The general proof and theorem-scale execution are not established by these tests. |
| `subsec:sharp-dense`, `sec:hashes` -- sparsification and parity tests for arbitrary clause density | **Not implemented.** |
| `sec:setup`, `sec:construction` beyond the bounded-occurrence case -- one factor per sparse polynomial equation, `M_0`/`C^B` at the general incidence parameters | Partially: the factor interface is general rational polynomials, but only the `b, w <= 3` bounded-occurrence instance is exercised. |
| `app:sparsify`, `app:arithmetic` | Partially: `eth_arithmetic/` covers the ring and canonical lifts; the sparsification tree is absent. |
| `app:quantitative` beyond `app:tensor` (circuit lower bounds, local inversion) | **Not implemented.** |

So the build is a bounded reference for two appendices/sections, not a
reference implementation of the paper. Any statement that the repository
"implements the algorithm" should be read as "implements the contraction
appendix and the linear-summary construction".

## 6. Reproducing

```sh
PYTHONPATH=src python -m pytest -o addopts="" -q tests/test_openai_paper_conformance.py
```

The suite also hashes the vendored source against the published SHA-256
values, so a change to `paper/` fails loudly instead of silently decoupling
the code from the formulas it claims to implement.

## 7. Fixes made when the source was pinned

Before the paper source was available, several defects survived because
nothing could check the code against the formulas it claimed to follow.

1. **Release manifest.** `scripts/verify_manifest.py` failed: three hashes
   were stale (`tapered_hermite.py`, `eth_recursive_contraction_v39/__init__.py`,
   `mode_bound.py`) and three files were unlisted. Regenerated.
2. **Eight-wire v4 experiment.** `scripts/validate_tapered_v4.py` relied on
   the `RecursionPolicy` default `max_work=2_000_000`, but the run charges
   about 2,132,619 units, so both `--write` and `--replay` failed closed with
   no count. The script now pins `max_work=3_000_000`, and a replay failure
   reports the transcript's `recorded_max_work`.
3. **Sparse packet sources.** `implicit_sparse_mode_source` was accepted by
   the point-mode path but not by the group-child path, which indexed
   `packet['slots']` directly. Every packet-source consumer
   (`lazy_children`, `jet_tiles`, `implicit_children`, `extension_modes`,
   `children`, `packet`, `reference`, `constructor`, `checker`) now goes
   through `real_packet_slots`, and the v31 tile checker accepts both
   schemas. `tests/test_sparse_packet_source_equivalence.py` pins the
   invariant: dense and sparse sources must yield identical tile modes,
   identical point modes, and identical child expansions.
4. **Labeler table cap.** The incremental conditional-expectation labeler
   stores one record per unordered edge pair, i.e. `O(M**2)` live state,
   and `max_work=None` removed the only guard. `assign_full_d3_labels` now
   fails closed on a pair-record cap (default 250,000), overridable
   explicitly.
5. **`replay_point_mode_matching_zero`** built its `_Work` meter inside the
   `try` and read it in the `except` handler. Hoisted.
6. **Doc accuracy.** The four-wire two-level audit was described as
   exhausting a "25-second cooperative budget"; it exhausts the work-unit
   cap after about 14 seconds. Corrected.

None of these change a mathematical claim. They make the release gate pass,
make the documented experiments reproduce, and make the code/paper
correspondence checkable.


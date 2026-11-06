# R9.1 formal refinement audit

This document separates three things that are easy to conflate:

1. **Kernel-checked Lean theorems** about definitions in `proofs/`.
2. **Executable evidence** from running CPython, the C++ backend, and the Lean
   evaluator on identical inputs.
3. **Open obligations** that neither of the above establishes.

Nothing in this repository claims the October 2026 OpenAI theorem, a
subexponential running time, or that a passing test is a proof.

## The source-to-model trust boundary

`src/veritas/research/eth_packing_v26/streaming.py::_candidate_score` is a
CPython function. `proofs/D3PythonScoreModel.lean` contains a Lean
transcription of it. A theorem about the transcription is **not** a theorem
about CPython. The boundary is crossed in two independent ways:

| Boundary | Mechanism | Strength |
|---|---|---|
| CPython → Lean transcription | line-by-line audit in this document plus the differential corpus in `scripts/validate_r91_python_model.py` | tested, not proved |
| Lean transcription → abstract score | `py_side_unknown`, `py_side_mismatch`, `pyPairUnknown_eq`, `pyPairMismatch_eq`, `sumBy_pythonEdgePairs` | kernel-checked |
| abstract score → `concreteD3ScoreCandidate` | `pyCandidateScore_eq` | kernel-checked |
| C++ → CPython | exact integer comparison over a randomised corpus and the fixture (`tests/test_r91_cpp_backend.py`) | tested, not proved |

The C++ backend is therefore *not* formally verified. It is an independently
coded implementation whose exact outputs agree with the reference on every
case that has been run.

## Line-by-line transcription audit

`_candidate_score(edges, partial, *, r, a, D, vertex, label, work)`:

| CPython | Lean |
|---|---|
| `value(side, ident, coordinate)` returns `label[coordinate]` when `(side, ident) == vertex`, else `partial.get(...)` | `pyValue`, with the same shadowing order |
| `for i, (u, v) in enumerate(edges): for w, z in edges[:i]` | `pythonEdgePairs`, the index-based enumeration `(edges[j], edges[i])` for `j < i` |
| `work.tick()` per pair visit | `pair_term` charges one unit per pair |
| `if left == right: continue` | `pyCompUnknown`/`pyCompMismatch` both start with `left != right` |
| `if x is not None and y is not None: if x != y: possible = False` | `pyCompMismatch` |
| `else: unknown += 1` | `pyCompUnknown` |
| early `break` out of both loops on mismatch | the pair term is `0`; the Lean term is also `0` because `concreteD3PairTerm` returns the empty constraint set |
| `total += 2 * (D // r ** unknown)` | `pyPairTerm` uses `r ^ (2*a) / r ^ unknown`; `Nat` division is exact because `unknown <= 2*a` |
| `total = m * D` | `edges.length * r ^ (2*a)` |

The transcription is *literal* in the sense that it keeps the index-based
pair loop and the early-exit scan. `sumBy_pythonEdgePairs` proves that this
enumeration has the same additive value as the unordered pair list used by
`concreteD3ScoreCandidate`.

## What is proved

`proofs/D3PythonScoreModel.lean` (22-module gate, no `sorryAx`):

* `py_side_unknown` — the Python `unknown += 1` branch is exactly the
  `.unresolved` classification of `classifyEquality`, including the
  current-vertex substitution.
* `py_side_mismatch` — the Python `possible = False` branch is exactly
  "classified as `.mismatch`, or the candidate symbol contradicts a recorded
  constraint".
* `pyPairUnknown_eq` — the pair-level unknown count is the sum of the
  per-coordinate `.unresolved` indicators over `concretePairCoordinates`.
* `pyPairMismatch_eq` — the pair-level mismatch flag is the `any` of the
  per-coordinate mismatch flags.
* `sumBy_pythonEdgePairs` — the index-based pair enumeration has the same
  additive value as `unorderedEdgePairs`.
* `pyCoordUnknown_add_fixed` and `fixedCount_constraints` — the per-coordinate
  bookkeeping identifying `parentUnknown - fixedCount` with the Python unknown
  count;
* `coordinate_constraint_wordMatches`, `wordMatches_range_any`,
  `pyPairMismatch_iff`, `pyPairUnknown_eq_parent`, `pyPairTerm_eq`, and
  `pyCandidateScore_eq` — the complete score identity.

`proofs/D3PythonOrder.lean`:

* the sorted vertex order is duplicate-free, covers every edge endpoint, has
  all rows before all columns, is ascending within each side, and is invariant
  under edge permutation;
* `d3_python_order_audit_fixture` evaluates the Lean definitions on
  `[(0,0),(1,1),(0,1)]` with `r = 2`, `a = 1` and obtains vertices
  `R0, R1, C0, C1`, labels `0, 1, 0, 1`, scaled scores `22, 16, 16, 12`, and a
  final class-square score of `12`. The CPython builder returns the same
  numbers; see `tests/test_r91_cpp_backend.py::test_fixture_matches_python_reference`.

`proofs/D3PacketBijection.lean`: the padded-slot / packet-position bijection,
described in `docs/R91_PACKET_BIJECTION.md`.

## The score identity (proved)

The chain from the Python branches to `concreteD3ScoreCandidate` is closed.
Each step below is a kernel-checked theorem in
`proofs/D3PythonScoreModel.lean` with no `sorryAx` and only the Lean
foundation axioms (`propext`, `Classical.choice`, `Quot.sound`).

1. `coordinate_constraint_wordMatches` — for one pair coordinate, the single
   `Option Nat` constraint generated by `coordinateConstraint` agrees with the
   two Python candidate comparisons.  The hypothesis `atMostOneCandidate`
   makes the single-constraint encoding lossless; it holds because a row
   candidate forces `current.1 = row` and a column candidate forces
   `current.1 = col`, which is impossible for one `current`.
2. `wordMatches_range_any` — `wordMatches` over
   `constraintsFromCoordinates ((List.range a).map g)` is the negation of the
   coordinate-indexed candidate scan.  This is the list-alignment lemma that
   was previously open; it is proved by induction on `a`, rewriting
   `List.range (a+1)` to `0 :: map succ (range a)` and using
   `List.getElem?_cons_succ` for the index shift.
3. `pyPairMismatch_iff` — the Python early-exit scan is
   `pairHasMismatchB ps || !(wordMatches (constraintsFromCoordinates ps) word)`.
4. `pyPairUnknown_eq_parent` — the Python unknown count is
   `pairUnknownComparisons ps - fixedCount (constraintsFromCoordinates ps)`,
   from `pyPairUnknown_eq`, `pyCoordUnknown_add_fixed`,
   `fixedCount_constraints`, and `Nat.eq_sub_of_add_eq`.
5. `pyPairTerm_eq` — the Python pair term equals
   `pairTermCandidate r a (concreteD3PairTerm ...) word`, by case analysis on
   the class mismatch and on `wordMatches`.
6. `pyCandidateScore_eq` — summing over `pythonEdgePairs` (which
   `sumBy_pythonEdgePairs` identifies with `unorderedEdgePairs`) gives
   `pyCandidateScore s current word r a edges =
    concreteD3ScoreCandidate s current r a edges word`.

The remaining boundary is **not** mathematical: it is the statement that
CPython executes this transcription.  That is audited line by line above and
tested by `scripts/validate_r91_python_model.py`; it is not proved.

## One-step and full-run correspondence

`d3CanonicalRun` selects `(labelWords r a).minOn score`, the first minimiser
in lexicographic order. CPython selects `min` over `(score, label)` tuples,
which is also the first minimiser because `itertools.product` enumerates
lexicographically. Turning that observation into a theorem needs:

* `labelWords` is strictly increasing lexicographically and duplicate-free;
* a fold lemma showing the Python-style "keep the smaller tuple" scan returns
  the first minimiser.

Neither is in this release. The full-run induction
(`pyRun = d3CanonicalRun` on `d3PythonOrderedVertices`) depends on both, so it
is not attempted. The fixture in `D3PythonOrder.lean` is a kernel-checked
instance, not the general statement.


## Paper conformance review (R9.1)

The formalization and the implementation were checked against
`paper/quantitative-contraction.tex`, not against the project's own prose.

### `eq:tensor-packing-conditions` and `lem:tensor-packets`

| Paper | Formalization / code | Status |
|---|---|---|
| `D_arr = r^{2a}`, `L = 2^a` | `r ^ (2*a)`, `2^a` everywhere | match |
| `M >= 2 D_arr^2 Delta` | `d3_preconditions` key `M_ge_2_D_squared_delta`; Lean `hregime` | match |
| `M >= L D_arr` | `M_ge_LD`; Lean `hwidth` | match |
| `2L <= Delta` | `2L_le_delta` | match |
| `E sum (X-M/D)^2 <= 2 M Delta` | `scaled_pair_second_moment_sub_square_le` | match |
| every load `<= M/D + sqrt(2M Delta)` | `d3_generated_class_load_bound` proves the stronger `D*X <= 2M` | match |
| `H_pad <= 3M/D_arr` | `d3_generated_padded_load_bound`, `d3_any_order_padded_bound`, `d3_python_order_padded_bound` | match |
| at most `3M/L` packets | `d3_generated_packet_count_bound`, `d3_python_order_packet_count` | match |
| at most `3M/r` ports per coordinate/symbol/side | `d3_generated_symbol_port_bound`, `d3_python_sorted_order_port_bound` | match |
| `M` edges occupy padded slots | `d3_edge_slot_accounting` | match |

The independent checker recomputes the same three inequalities with exact
`Fraction` arithmetic (`packet_count_bound`, `port_load_bound`,
`initial_variance_bound` in `streaming_check.py`), and it is not the
production scorer.

Two numeric consequences were re-derived and confirmed:

* `a >= 2` in the active regime, so `L >= 4`, `D_arr = 64^4 = 2^24`,
  `Delta >= 8`, and the first packing inequality forces `M >= 2^52`
  (`inspect_active_theorem_capacity` returns `2^52` exactly).
* for `r = 2, a = 1, Delta = 2` the smallest instance satisfying
  `M >= 2 D^2 Delta` is `M = 64`; `D*H = 64 <= 3M = 192` and the checker
  accepts packet and port bounds.

### `lem:tapered-hermite`

| Paper | Code | Status |
|---|---|---|
| `h = ceil(3M/u)` | `h=(3*M+u-1)//u` | match |
| `q_t = h max(0, u - v_2(t))` | `q=h*max(0,u-i)` | match |
| `D_t = L/2^i`, `p_t = p + 8hD_t + 8M(a+1)` | `prec=p+8*h*(L//(1<<i))+8*M*(a+1)` | match |
| `alpha = 2^{a+1}` | `alpha=1<<(a+1)` | match |
| degree `<= M(2L-1)` | `deg=M*(2*L-1)` | match |
| `1 <= u <= a`, `M >= u` | `if u > a or u > M: raise` | match |
| `sum_{t != 0} q_t > M(2L-1)` | `sum(multiplicity) <= deg` raises | match |

The formulas match; the *lemma* is still not proved, and the recursive
construction that would consume these plans remains unimplemented.

### Executable semantic check

`_candidate_score` was compared with a brute-force exact-rational
conditional expectation `D * E[sum_gamma X_gamma^2 | partial + label]` over 40
random small graphs, all partial states, and all labels. Zero mismatches. The
paper's variance bound `D*E[sum X^2] - M^2 <= 2 M Delta D` was checked the
same way on 30 random graphs with zero violations.


## Defects found in this review and fixed

1. **Out-of-bounds read in the pybind11 layer.** `veritas_d3.candidate_score`
   and `veritas_d3.vertex_scores` forwarded `row_assignments` /
   `column_assignments` to the C ABI, which indexes
   `assignments[index * dimension + coordinate]` up to
   `vertex_count * dimension`.  A short vector was accepted and read past its
   end (reproduced: a one-element vector for a two-vertex table returned a
   score instead of failing).  The bindings now enforce
   `assignments.size() == ids.size() * dimension` before the call.
   Regression: `test_binding_rejects_misshapen_assignment_tables`.

2. **`auto` backend diverged from the reference on wide vertex ids.** The
   native ABI carries ids as `int64`, so `2**63` was accepted by
   `score_backend="python"` but raised with `"cpp"` *and* `"auto"`.  `auto`
   now falls back to the reference for ids above `INT64_MAX` and records
   `backend_fallback_reason` on the returned build object; an explicit `"cpp"`
   request still fails closed.  The certificate schema is unchanged.
   Regression: `test_wide_vertex_ids_are_explicit_backend_boundary`.

3. **Silent `sorryAx` regression from an import change.** Narrowing
   `D3PacketBijection`'s import to `D3SymbolPorts` made
   `d3_offset_address_inverse` unknown, so `encode_decode` became
   `sorry`-backed.  `#print axioms` reported `[sorryAx]`; the module now
   imports both.  This is why the gate checks exact axiom reports.

4. **Stale hardening test against the renamed release archive.**
   `scripts/build_release.py` now emits a fixed release name plus a
   `*.manifest.json` sidecar; `test_optimized_builder_refreshes_both_manifests_and_zip`
   still asserted the old `<dir>_FULL_UPGRADED.zip` path.  The test now checks
   the new name and the sidecar digest.

## Executable refinement evidence

`scripts/validate_r91_python_model.py` evaluates the Lean transcription and
CPython on the same corpus and compares the integers. That is evidence about
the CPython → transcription boundary; it is not a proof. See
`validation/r91_python_model.json`.

## Negative and fault-injection coverage

`tests/test_r91_cpp_backend.py` covers: the ordering fixture, edge
permutations, duplicate edges, empty and singleton graphs, equal numeric IDs
on both sides, tied candidate scores, radix 2 and 3, dimensions 1 and 2, large
integer scores, budget exhaustion, malformed inputs, and fallback behaviour.
`tests/test_lean_proof_gate_audit.py` and
`tests/test_lean_proof_gate_fault_injection.py` cover the proof gate:
unauthorised axioms, weakened theorem contracts, wrong toolchain, and wrong
manuscript hash.

# R9.6 mathematical and proof obligations

Status vocabulary used here, strictly:

| Label | Meaning |
|---|---|
| **implemented** | the code path exists and runs |
| **tested** | exercised by an automated test in this release |
| **independently checked** | a second implementation, sharing no arithmetic, agrees |
| **Lean-compiled** | a kernel-checked Lean 4 theorem exists for the *model* statement |
| **proved** | a Lean theorem whose statement covers the executable contract |
| **open** | no proof exists in this release |
| **not run** | the check could not be executed; recorded with its blocker |

A passing bounded test is never "proved".  A skipped check is never "passed".

---

## 1. The rings

```
R_pc = (Z/2^pc Z)[U] / (f(U)),   deg f = e,  f irreducible over GF(2)
J_{pc,ell} = R_pc[z] / (z^ell)
```

* implemented, tested, independently checked (integer polynomial long reduction
  in `independent_r95/recipe_oracle.py`).
* Representative choice, unit test, valuation, Hensel inversion: implemented,
  tested.
* The canonical lift `R_pc -> R_P` is **not** a ring homomorphism; this is
  stated in `docs/R96_EXACT_RING_CONTRACT.md` §3 and pinned by
  `tests/test_source_hermite_formula.py` and the creation-lift tests.
  *Open*: a formal statement of the lift's exact algebraic status.

## 2. Packet coefficient extraction

Identity, for a Boolean index `bits`:

```
value(bits) = [ prod_i (c_i + sum_m l_i[m] z_m) ]_{z^beta}
              * prod_s ( sum_{j: bits[col_j]} src_s[j] )^{beta_s}
```

with `c_i = l_i` if `bits[row_i]` else `1 - l_i`, and
`l_i[m] = ±coeff_m[i]` by the same sign rule.

* `first_order` (one mode, exponent one) is the product rule
  `sum_i l_i prod_{j<i} c_j prod_{j>i} c_j`.  implemented, tested,
  independently checked against a plain integer polynomial expansion in
  `adversarial/check_r96_independently.py`.
* `sparse_dp` (general) is truncated polynomial multiplication over completable
  exponent vectors.  implemented, tested, independently checked against
  `unpruned_reference` and against `independent_r95.recipe_oracle` on 48
  randomized seeds × every Boolean index.
* **Pruning soundness.**  A term is dropped only when the ring element is
  exactly zero or its exponent vector can no longer be completed.  Both are
  identities in the truncated polynomial ring.  Dropping a term because a
  *single modular coordinate* is zero would be unsound and is never done.  This
  is a written argument, not a mechanized proof.  *Open*: mechanized pruning
  soundness.
* **Not claimed**: any bound on the number of DP states in terms of the mode
  exponents.  The state cap refuses; it does not bound.

## 3. The finite parent-to-all-children identity

Statement certified by `VERITAS_PARENT_CHILD_CERTIFICATE_V1`, for one recursion
level:

```
ParentValue(t, zeta) == SUM over every admissible beta of
                          weight(beta, t) * Product over groups
                                             ChildValue(group, beta, t, zeta)
```

* Domain: `structural_tuples(modes, precision)` — every exponent vector
  componentwise within each mode's row capacity with total weight below the
  node precision, in deterministic lexicographic order.
* Certified fixture: two wires, `e = 2`, `p = 4`, `a = u = 1`, radix 4.
  `points_checked = points_required = 8`, `classification = FULL_COVERAGE`.
* implemented, tested, independently checked (the consumer re-derives the
  domain and recomputes every term; the parent side uses the half-edge oracle,
  a different code path from the child contraction).
* **Explicitly not claimed.**  This is *not*:
  * recursion beyond the first level — observed depth is one;
  * the manuscript's `M/8` shrinking condition — the fixture is two wires and
    the R9.5 eight-edge→six-edge observation is not a proof of it;
  * complete mode coverage for any parameter regime outside the fixture;
  * a complexity statement.
* *Open*: a universal statement of the identity over all source-admitted
  states; a proof that the admissible domain enumeration is complete for the
  manuscript's mode set.

## 4. The unreachable source-active schedule

Derivation (executable, `source_regime.active_parameter_contradiction`):

```
lambda = ceil(log2(s));   e = 4*lambda;   e <= max_extension_degree
  => lambda <= max_extension_degree / 4          (64 -> 16; ceiling 4096 -> 1024)
s.bit_length() <= max_size_bits                  (ceiling 65536 -> lambda <= 65536)
base = floor(lambda / 131072);  active needs base >= 1  =>  lambda >= 131072
131072 > 1024
```

* implemented, tested (including a direct check that `schedule_preflight` never
  returns `ACTIVE_NUMERIC_PRECONDITIONS_MET` for `lambda` up to 1024).
* This is a **parameter contradiction in the current representation**, not a
  refutation of the manuscript.
* **Raising the caps is not a fix.**  `s = 2**131071` has ~39,500 decimal
  digits and needs `e = 524288`; no materialized graph, ring or description of
  that size is executable here.
* Two regimes are separated: `EXPERIMENTAL_SCALED_FINITE` (what runs) and
  `SOURCE_THEOREM_PARAMETERIZED` (what is described but not executed).  Every
  admitted context returns `INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED`
  and theorem mode stays disabled.
* *Open*: a scalable symbolic representation with proven refinement.  The
  obligations are listed by `SymbolicSourceSize.refinement_obligations()` and
  are all undischarged: parent-to-child derivation as a function of `lambda`,
  width bounds at every depth without enumerating modes, the shrinking bound as
  an exponent inequality, and the connection to the executed finite code.

## 5. Hermite recovery

* Coefficientwise precision requirement: `pt = p + 8hD + 8M(a+1)` with
  `h = ceil(3M/u)`, `D = L >> v2(t)`.  implemented, tested, and recomputed from
  the closed form in `tests/test_r96_hermite_audit.py` (no import of the
  production formula).
* Interpolation grid size and distinctness: `degree_bound + 1` samples from
  pairwise-distinct residues, so every denominator is a unit.
* **Convention.**  A jet holds the *coefficients* of `F(t + alpha z)`, not
  derivatives.  Verified by sampling an explicit integer polynomial and by an
  independent check that
  `sum_{t,j} w[t][j] * [z^j] F(t + alpha z) == F(0)` for every monomial up to
  the degree bound.
* **Repeated roots.**  `F(z) = (z-1)^3` is recovered exactly at precision 12.
* **Historical regression preserved.**  `F = 19` recovers `19`; the forged
  recovery weight that once produced `6` is still rejected.
* *Open*: a universal functional and coefficientwise precision proof through
  every recursive depth.  Only bounded fixtures are checked.

## 6. Recursive invariants

* Child size/degree/precision constraints: checked per constructed child
  (`verify_constructed_child_recipes`, `actual_child_certificate`), bounded.
* **Parent-to-child size decrease**: checked only as the necessary condition
  `32 * child_edges <= 3 * parent_edges` in `check_source_transition`, and as
  `r * child_edges <= 6M` in the certificate.  *Not proved* for the applicable
  regime; the observed eight-edge→six-edge fixture does not establish the
  manuscript's `M/8` condition.
* Complete tuple and point requirements at every depth: only at depth one, in
  the certified fixture.  *Open* for depth > 1.
* Height/valuation and bit-width growth: recorded in the ledger
  (`accumulator_operand_bits`, `maximum_accumulator_operand_bits`), not proved.
* Work, memory, reconstruction and verification charges: recorded, with an
  explicit `unmeasured` list.  **No claim of complete accounting.**
* Termination and error propagation: fail-closed at every cap; *open* as a
  proved termination theorem.

## 7. Lean

* Toolchain: `leanprover/lean4:v4.35.0`, commit
  `eb6cafb7290e8bd5f2937522d8d804f58f02bafc`, installed in this session.
* Gate: **36 modules compiled from source, `PASS`**, axioms exactly
  `propext`, `Classical.choice`, `Quot.sound`.
* Scope: the Lean statements are *model* results about coordinate
  representatives, packing models, keyed runs and finite packet domains.  They
  are **not** refinements of the Python or C++ implementations.
* `lean_python_builder_refinement_proven` is `false` in the gate output and
  must stay false until an explicit refinement map is proved.
* *Open*: the refinement map from each Lean model to its Python implementation,
  and any theorem covering the executable contract.

## 8. C++ backend

* Rebuilt on macOS/arm64 with Apple clang 21, C++20, `-Werror`.
* `veritas_d3_selftest`: `PASS`.
* Differential suite: `PASS_FINITE_CPP_DIFFERENTIAL`, backend `cpp-ctypes`,
  6 independent certificate replays, large-integer exactness on both sides.
* *Not claimed*: the C++ path is not formally verified, and the pybind11 module
  was not exercised (the ctypes ABI was).

## 9. Complexity

Nothing in this release supports a running-time, space, source-refinement, SAT
or #SAT theorem.  `subexponential_runtime_proven`, `polynomial_space_proven`
and `competitive_solver_performance_claimed` are `false` in every emitted
document.  The measured speedup of the first-order path is a statement about
one algorithm on one machine, not an asymptotic result.

---

## Obligation register

| # | Obligation | Status |
|---|---|---|
| 1 | Mechanized pruning soundness for the sparse DP | open |
| 2 | Universal mode-domain completeness | open |
| 3 | Parent-to-children identity at depth > 1 | open |
| 4 | Manuscript `M/8` shrinking bound | open |
| 5 | Universal Hermite functional and precision proof | open |
| 6 | Lean → Python refinement map | open |
| 7 | Source-active executor and its schedule | open (unreachable in this representation) |
| 8 | Proved termination and complete work/space accounting | open |
| 9 | Arbitrary-density count-preserving reduction and the #SAT theorem | open |
| 10 | Independent reproduction of the whole release on a second platform | not run |

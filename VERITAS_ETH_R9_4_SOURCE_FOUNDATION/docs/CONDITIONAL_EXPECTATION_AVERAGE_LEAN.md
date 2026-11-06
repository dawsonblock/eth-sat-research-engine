# Conditional-expectation averaging proof

## Scope

`proofs/ConditionalExpectationAverage.lean` formalizes the finite arithmetic
used by the candidate-label step in `lem:tensor-packets` of the pinned
`paper/quantitative-contraction.tex`. It proves the averaging identity for an
abstract list of pair contributions described by coordinate constraints and
still-unknown equality comparisons. It does not prove the manuscript's full
packing lemma.

The proof has these stages:

1. `countSatisfyingWords` proves that a length-`a` label vector satisfying a
   valid partial coordinate assignment has exactly `r^wildcardCount`
   completions.
2. `constrained_pair_average` sums one compatible pair contribution over all
   `r^a` candidate labels. Each newly fixed comparison multiplies a matching
   contribution by `r`; the number of matching candidates decreases by the
   same factor.
3. `conditional_pair_term_average` rewrites the production-style scaled
   quotient `r^(2a) / r^unknown` as an exact power. It assumes the active term's
   constraint vector has length `a`, its newly fixed comparisons are among the
   still-unknown comparisons, and the total unknown count is at most `2a`.
   Incompatible terms are represented by `constraints = none` and contribute
   zero on both sides.
4. `conditional_pair_sum_average` lifts the identity to every term in a finite
   list. `conditional_score_average` adds a candidate-independent base term,
   matching the `M*D` diagonal contribution in the executable score.
5. `coordinate_pair_term_average` defines a row and column comparison status
   for every coordinate of one edge pair. A valid coordinate has no prior
   mismatch, has at most one comparison that depends on the current candidate,
   and uses an in-range fixed symbol. From these local conditions, Lean proves
   the constraint-vector length, that each newly fixed comparison was counted
   as unknown, that at most `2a` comparisons are unknown, and that every
   target symbol is valid. `coordinate_pair_sum_average` and
   `coordinate_score_average` lift the result over a list of these pair-state
   vectors.

The algebra is over natural numbers and uses exact divisibility of powers of
`r`; the Lean proof does not divide by a nonunit modulo a ring. `coefficient`
allows the factor `2` used for unordered edge pairs.

## Executable correspondence and independent checks

`streaming.py::_candidate_score` computes the scaled conditional expectation
directly from edge pairs. For an edge pair and coordinate, it skips identical
endpoints, rejects a term after a known mismatch, counts an unresolved
comparison in `unknown`, and otherwise contributes
`2 * (r^(2a) / r^unknown)`. A candidate label resolves comparisons to fixed
opposite endpoints. This is the intended refinement into
`ConditionalPairTerm`:

| Lean field | Executable interpretation |
|---|---|
| `constraints = none` | Previously fixed comparison already mismatched; pair contribution is zero |
| `constraints = some cs` | Candidate must match the fixed opposite endpoint in each constrained coordinate |
| `fixedCount cs` | Number of candidate-dependent comparisons among the unknown comparisons |
| `parentUnknown` | Number of unresolved row/column comparisons before choosing the candidate |
| `coefficient` | `2` for each unordered edge pair |
| `base` | `M*D` diagonal terms, independent of the candidate |

The `PairComparison` status vocabulary represents each of the row-side and
column-side equality checks in one coordinate: `resolved` means already true
or reflexive; `unresolved` means its probability remains `1/r` and the current
candidate does not resolve it; `candidate target` means the candidate must
equal a fixed opposite endpoint; and `mismatch` makes the whole edge-pair term
zero. `coordinateIsValid` rejects a prior mismatch and rejects two
candidate-dependent comparisons in one coordinate. For an actual bipartite
edge pair, the latter condition follows from assigning a side-tagged vertex:
it cannot be both a row endpoint and a column endpoint. The code-to-status
classifier for arbitrary graph pairs and partial assignments has not yet been
formalized; the finite Fraction test is the current executable check of that
translation.

`proofs/ConcreteD3ConditionalExpectation.lean` now closes the formal
edge-pair-classification gap. It defines the row/column endpoint classifier
for actual edges, proves that one side-tagged vertex cannot create two
candidate-dependent comparisons in a coordinate, maps an already mismatched
pair to the zero term, and proves the candidate-average identity for every
finite edge list. It also models the production rule that the current vertex's
candidate value overrides a stored assignment. The theorem
`concrete_d3_score_average` is therefore stated over actual row/column edge
pairs rather than caller-supplied abstract comparison states.

The same module now proves
`ordered_overlap_count_le_two_m_delta`: for a finite bipartite edge list with
maximum row and column degrees at most `Delta`, the number of ordered edge
pairs sharing at least one endpoint, including diagonal pairs and counting
parallel edge occurrences separately, is at most `2*M*Delta`.

`proofs/D3VarianceBound.lean` adds a separate finite pair-marginal counting
model. For each ordered edge pair, `edgePairLabelSamples` enumerates labels on
its distinct row and column endpoints; shared endpoints receive one sampled
word, while distinct endpoints receive independent words. It proves the
sample length, the exact agreement count `r^(2*a)`, and the identity
`D * Pr[the edge-pair labels agree] = r^(2*a - unknown)` as an integer
product identity, without division. Disjoint endpoint pairs have scaled
centered contribution zero. Every overlapping pair contributes at most
`D = r^(2*a)`. Composing that result with
`ordered_overlap_count_le_two_m_delta` proves
`scaled_centered_pair_sum_le`, the finite pair-marginal bound
`D * E[Phi] <= 2*M*Delta*D` in the model represented by those local samples.
The theorem `scaledPairSecondMoment_eq_centered_add_mul` identifies the
pairwise second moment minus `M^2` with that centered sum, and
`scaled_pair_second_moment_sub_square_le` gives the resulting bound directly.

`proofs/D3SelectionBridge.lean` composes the concrete edge-list averaging
identity with the finite minimum theorem in
`proofs/ConditionalExpectationSelection.lean`. For every valid partial state
and current side-tagged vertex, it proves there exists a legal label word
whose modeled conditional score does not increase. This closes the formal
one-step selection lemma, but it does not yet define or prove the repeated
vertex-assignment recursion or the Python tie-breaking/refinement.

This is stronger than the prior abstract conditional-expectation proof, but
it is not yet the complete global probability-space theorem. The Lean code
does not define the full product space of labels for all graph vertices and
prove that its load potential expands to this sum of pair marginals. It also
does not prove that the Python implementation refines the Lean model.
The finite refinement check
`test_partial_state_candidate_average_matches_fraction_oracle` still compares
the Python score with the independent rational implementation on seeded
partial states. Those checks validate finite instances, not universal Python
refinement.

## What remains open

The remaining probability-space bridge must connect the common product
labeling model and the source potential to the finite pair-marginal sum, then
connect the source score to the Python score and compose one-step choices
across the full canonical vertex sequence. Packet padding/address
construction, port-load bounds, and polynomial bit-time/space analysis still
need universal proofs. No active theorem-scale packing was executed. The
theorem path remains disabled.

## Reproduction

With Lean 4.35.0 from the checked `lean-toolchain` available on `PATH`:

```sh
LEAN_BIN=/path/to/lean-4.35.0/bin/lean python scripts/validate_conditional_expectation_lean.py
PYTHONPATH=src python -m pytest -o addopts= -q tests/test_d3_streaming_independent.py
```

The validator compiles the base, concrete-edge, and pair-marginal modules in
dependency order into a temporary directory, checks the central theorem
names, and rejects `sorryAx`. The reported axioms include Lean foundation axioms such as
`propext`, `Classical.choice`, and `Quot.sound`. The Python test is an
independent finite oracle comparison, not a proof artifact.

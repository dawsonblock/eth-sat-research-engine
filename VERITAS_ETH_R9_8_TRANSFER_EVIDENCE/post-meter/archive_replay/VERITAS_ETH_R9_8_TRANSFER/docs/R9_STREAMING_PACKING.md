# R9 streaming packing stage

## Scope and pinned source

This stage targets `lem:tensor-packets` and its hypotheses
`eq:tensor-packing-conditions` in the pinned manuscript file
`paper/quantitative-contraction.tex` (SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`).
The paper tree hash recorded in `docs/OPENAI_PAPER_CONFORMANCE.md` is
`f4a10137d8630cb8ff26d031aca38c23a39db4606a4494ff7e43f59b8c671594`.
The source labels used here are `app:tensor`, `lem:tensor-packets`,
`eq:tensor-packing-conditions`, and the child-load consequence in
`subsec:tensor-children`. Historical Appendix-D names are not used as
authority.

The active-call inequalities are checked with exact integers before the
labeler runs:

\[
M\ge 2D_{\rm arr}^2\Delta,\qquad
M\ge LD_{\rm arr},\qquad 2L\le\Delta,
\quad D_{\rm arr}=64^{2a},\quad L=2^a.
\]

`construct_active_call_streaming_packing` selects radix 64 and checks the
three inequalities using the graph's actual maximum degree. If an inequality
fails it returns `INCONCLUSIVE_D3_PRECONDITIONS` with no packing or
certificate. Despite the historical function name, it receives neither the
source size `s`, depth `d`, nor the global bound `Delta = ceil(s^(9/10))`;
it cannot qualify a manuscript active call.

## Construction and finite checks

`src/veritas/research/eth_packing_v26/streaming.py` assigns a complete label
from `[r]^a` to each row-side and column-side vertex. The vertex order is
sorted by side and integer ID. At each vertex it streams all `r^a` candidate
labels in lexicographic order, computes the exact conditional expected square
load by scanning unordered edge pairs, and selects the lexicographically first
minimizer. It stores no edge-pair table. Its live construction state is the
edge list, current partial labels, current class lists, and one candidate
label; the algorithm and returned packing still require memory proportional
to the finite input and output. The edge-pair scans are polynomial but can be
impractical, and hard work/candidate caps fail closed.
This finite implementation also caps the label dimension at `a <= 64` before
computing powers or packet widths; the active wrapper returns
`INCONCLUSIVE_RESOURCE_LIMIT` above that bound.

For `D=r^(2a)`, a candidate's scaled score is

\[
S=D\,\mathbb E\!\left[\sum_\gamma X_\gamma^2\right]
 = MD+2\sum_{e<f} D\Pr[\text{the two directed pair labels agree}].
\]

Each probability is evaluated exactly by counting unresolved independent
side-coordinate equalities; a forced disagreement contributes zero. The
constructor checks that the sum of all candidate scores is exactly
`r^a * previous_score` before committing the selected vector. The compiled
Lean lemma in `proofs/ConditionalExpectationSelection.lean` proves the
abstract finite selection fact: a nonempty list of natural scores with that
average contains a score no larger than the parent score. It does not prove
that the Python score routine refines the full global probability-space
potential.

`proofs/ConcreteD3ConditionalExpectation.lean` formalizes the row/column
endpoint classification for actual edge pairs and proves that at most
`2*M*Delta` ordered pairs overlap under the degree hypotheses.
`proofs/D3VarianceBound.lean` independently enumerates each pair's labels on
its distinct endpoints, proves `D * Pr[agreement] = r^(2*a - unknown)` as an
exact product identity, and bounds the sum of centered pair marginals by
`2*M*Delta*D`. This is a formal finite pair-marginal result. The global
product-labeling expansion and its exact correspondence with the executable
conditional score remain unproved.
`proofs/D3PotentialIdentity.lean` now proves the pointwise finite identity
that the sum of squared directed-class loads equals the number of ordered
equal-signature edge pairs, including its `r^(2*a)` scaling. This is the
collision-potential representation used by the source proof. It does not yet
identify the executable partial-state score with the conditional expectation
of this full potential; that remains a separate proof obligation. The Lean
validator compiles and checks both central theorems and records their source
hashes.
`proofs/D3CollisionBridge.lean` proves that the fixed-label scaled potential
equals its diagonal contribution plus twice the unordered pair collisions.
It also proves the same decomposition for the independently counted initial
pair marginals and derives the `M^2 + 2*M*Delta*D` upper bound for that
unordered-pair expression under the degree hypotheses. This establishes a
shared algebraic form; it does not prove that the executable conditional
score or its partial-state classifier refines either expression.
`proofs/D3InitialScore.lean` closes one specific classifier refinement: for
an empty partial assignment and positive radix, each concrete Lean pair term
equals twice the independently enumerated scaled agreement. The complete
initial Lean score therefore equals the pair-marginal second moment and
satisfies its degree bound. Later partial states and the Python implementation
remain separate proof obligations.
`proofs/D3SelectionBridge.lean` composes the concrete average with finite
minimum selection and proves existence of a nonincreasing label for one
current vertex. `proofs/D3CanonicalSequence.lean` defines a deterministic
first-minimum selector and a recursive vertex-labeling run. Its first
candidate meets the initial bound. For a full run, Lean proves monotonicity
only under explicit parent-score, child-score and readiness hypotheses; those
must still be established for the source potential and concrete state. The
Lean word-list order also has not been proved equivalent to Python's
lexicographic candidate order.
`proofs/D3StateInvariants.lean` instantiates readiness as a distinct list of
unassigned vertices. Lean proves assignment preserves this invariant, the
run keeps labels valid and preserves unlisted vertices, and every listed
vertex receives all `a` valid symbols. For a nonempty distinct list starting
from the empty state, the initial degree bound carries to the final potential
under two score-to-potential equalities as hypotheses. That module does not
establish those equalities or refinement to the Python implementation.
`proofs/D3ParentScoreIndependence.lean` defines the unmasked Lean state score
and proves that it equals the concrete parent score at any unassigned next
vertex, without assuming that equality. It specializes the conditional
full-run bound to this score, leaving the child-score transition equality as
an explicit hypothesis. This state score has not yet been proved to be the
global conditional expectation or a refinement of the Python code.
`proofs/D3ChildTransition.lean` proves that child-score transition equality
for the Lean classifier, including existing mismatches, new rejections, and
changes in unknown-comparison counts. It removes that hypothesis from the
canonical Lean run's raw-score bound. The result has not yet been connected
in that module to final realized class loads, the full global label probability
space, or Python's executable implementation.
`proofs/D3RealizedLoads.lean` establishes the final class-load connection. For
positive radix and the stated degree bounds, the Lean run over its own
deterministically deduplicated edge-vertex list proves
`D * sum_gamma X_gamma^2 <= M^2 + 2*M*Delta*D`, where `D = r^(2*a)`.
The vertex list is proved distinct and covers all edge endpoints. This is a
finite Lean labeling result, not a proof of packet padding, per-port bounds,
the paper's total cost, or equivalence with Python's sorted vertex order.
`proofs/D3ClassAccounting.lean` includes all `D` directed classes, including
empty ones, and proves their loads sum to `M` and their squared loads equal
the edge-indexed collision potential. `proofs/D3VarianceAlgebra.lean` proves
the centered squared-deviation bound and, under `M >= 2*D^2*Delta`, each
class load `X` satisfies `D*X <= 2*M`. With `M >= L*D`, its common size
`H = L * ceil(max_gamma X_gamma / L)` covers all classes, is a multiple of
`L`, and satisfies `D*H <= 3*M`. These are properties of the Lean-generated
labeling. `proofs/D3SymbolPorts.lean` proves that, for this Lean-generated
labeling and under the same degree and first two packing hypotheses, each
coordinate and symbol has at most `3M/r` real ports on either side. For
radix 64 it proves that the sum of the two group half-wire counts is at most
`3M/32` and, when `M>0`, strictly below `M/8`. This counts incidences in the
Lean graph; it is not yet a child-network construction or a proof that the
Python labeling refines the Lean labeling. The port bound also holds for any
distinct vertex ordering covering all edge endpoints, including a sorted
order if the executable refines the Lean state transitions. Packet-slot construction,
source-schedule induction, and the Python refinement remain open.
In fact, `d3_order_audit_fixture` and its companion Python test expose a
three-edge example where the Lean-generated ordering and Python's sorted
ordering produce different row labels. The arbitrary-order result avoids
assuming the two orderings coincide; it does not prove Python refinement.
`proofs/D3SlotSplit.lean` separately proves inverse operations for splitting a
Boolean slot word into copy and orientation bits according to an equality
mask, and proves the lengths of the resulting streams. It does not yet map
edge classes to packet indices or prove the implementation's slot address.
It also proves boundedness, injectivity, and an inverse for quotient/remainder
addresses within one directed class; composing these facts across classes and
unordered-symbol packets is still required. A one-coordinate lemma also
recovers an ordered pair from its sorted symbols and orientation bit.

`streaming_check.py` is a separately written finite checker. It does not
import the production score routine or packet constructor. It recomputes
candidate probabilities as exact `Fraction` products, checks every candidate
at every vertex, verifies the average identity and canonical minimizer,
reconstructs directed classes and implicit packet addresses, and counts the
actual row/column symbol ports. It checks `D H_pad <= 3M` and
`64 * max_port_load <= 3M` when their paper hypotheses are applicable. It
reports `universal_packing_lemma_proven: false` in all cases.

The finite packet-address checker independently derives, for each directed
class's ordered edge list, packet index and equal-coordinate copy bits. It
rejects duplicate addresses and verifies every input edge is represented
exactly once. No dense enumeration over all `D_arr` directed classes is used.

## Proof and evidence boundary

Lean 4.35.0 compiles the conditional-average, concrete edge-pair, finite
pair-marginal, one-step selection, abstract selection, and child-bound modules through
`scripts/validate_conditional_expectation_lean.py`; it rejects `sorryAx` for
the printed central theorems. The pair-marginal result closes the local
overlap/variance calculation, but not the global product-space expansion or
the Python refinement. The earlier standalone child-shrink theorem assumes
the row/column load inequalities. The new Lean labeling theorem derives them,
but it does not establish that the Python algorithm or a constructed child
has the same ports. Packet-slot construction and source-parameter induction
remain open.

The independent Python checker can replay finite instances, including a
generic-radix `r=2, a=1` 4-regular fixture satisfying all three numeric
inequalities. That fixture is explicitly not the paper's fixed-radix active
call: its source-radix flag is false. Our earlier statement that `a=1` is the
smallest active exponent was incorrect. In the source schedule an active
call has `u_d >= 1` and `a_d = 2 sum_{j<=d} u_j`, so `a_d >= 2` and is even.
The weakest numeric consequence with `a=2` is `D_arr=2^24`, `L=4`,
`Delta >= 8`, and `M >= 2^52 = 4,503,599,627,370,496`. This is only a
lower bound obtained from the displayed inequalities, not the full schedule
threshold; the source ties `Delta` to `s`. The default caps reject such a
run. No R9 run has produced a fixed-radix theorem-regime packing certificate.

Streaming certificate V2 always reports `paper_active_call_eligible: false`:
its schema does not carry the source schedule. V1 certificates may be
replayed using their historical interpretation, but the replay explicitly
discards their active-call claim. The compressed `a=1` K_N,N certificate has
the same legacy boundary; it checks a packing-lemma example only.

This stage does not prove the universal packing lemma, all-node mode
expansion, the parent-to-child identity, Hermite precision composition,
multilevel termination, bit-time or peak-space bounds, the arbitrary-density
reduction, or the paper's theorem. The theorem recursor remains
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

## Reproduction

From the repository root with Python 3.12 and the project test dependencies:

```sh
PYTHONPATH=src python -m pytest -o addopts= -q tests/test_d3_streaming_independent.py \
  tests/test_d3_implicit.py tests/manuscript_invariants/test_eth26_d3.py \
  tests/test_d3_conditional_expectation_independent.py
PYTHONPATH=src python scripts/validate_r9_streaming_packing.py
elan run leanprover/lean4:v4.35.0 lean proofs/ConditionalExpectationSelection.lean
elan run leanprover/lean4:v4.35.0 lean proofs/ConditionalChildShrink.lean
```

The generated finite validation record is
`validation/r9_streaming_packing.json`. Work units omit rational-number bit
cost, Python allocation, serialization and operating-system resource
measurements; they are not complexity bounds.

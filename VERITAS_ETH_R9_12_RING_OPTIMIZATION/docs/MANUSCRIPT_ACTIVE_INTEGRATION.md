# Finite active-path integration

The `contract_scaled` research API executes the same recursive traversal as the
public manuscript executor, including packing, the complete weighted mode domain,
sequential child calls, interpolation and Hermite recovery. The default public
`contract` schedule and source hypotheses are unchanged. Small ordinary calls
still use `SOURCE_DIRECT_RANGE` and are not evidence of source-active recursion.

## Completed finite check

Run:

```sh
PYTHONPATH=src python scripts/validate_manuscript_active.py --output-dir /outside/checkout/evidence
PYTHONPATH=src python scripts/validate_manuscript_active.py --replay /outside/checkout/evidence/active_scaled_certificate.json
```

The connected one-wire fixture has two polynomial-valued tensors:

- Row: `[1 + 2V, 3 + V]`
- Column: `[2 + V, 1 + 3V]`
- Arithmetic: modulo 4, truncated modulo V².

Direct integer contraction is `5 + 15V`, hence the expected modular answer is
`1 + 3V`. The recursive run has one active level, eight interpolation points,
38,480 full formal exponent tuples, and 76,960 sequential child calls. All four
padded packets, including the three empty packets, and all structurally zero
modes remain represented. A fixed column-label permutation makes the occupied
packet cross groups, exercising the mode sum rather than only a local kernel.

The independent replay imports none of the producer's tensor constructors,
entry evaluators, packing, mode, interpolation or recovery implementations.
It reconstructs the rational Cauchy polynomial, uses a separately implemented
extension ring to recompute every root interpolation value, and checks the final
answer by integer contraction. A separate generating-function recurrence checks
the full formal tuple count. Tamper tests cover inputs, point values, missing or
duplicate points, precision, packet inventory, field polynomial, output, counters,
child summary and false qualification flags.

This is a bounded numerical integration check. The compact transcript does not
contain every child entry or constitute a general independently replayable
recursive proof certificate. Traversal counters establish consistency with the
instrumented run, not a proof of arbitrary execution history.

## Explicit differences from the paper

- `a = u = 1`, radix 2 instead of 64.
- Leaves stop at the explicitly selected depth. Children do not shrink here.
- The local precision uses the exact denominator loss of the Hermite functional.
  For the ±1 triple-node fixture, its weights are `(1/2, ±5/64, 1/128)`.
  Thus root precision 2 requires local precision 9. The paper prescribes 66.
- Node multiplicities, interpolation degree, all required points, full padded
  inventory and full weighted mode domain are retained.
- Manuscript packing and shrinking-size hypotheses are not asserted.

At local precision 66 even this radix-2 one-wire example has
153,522,640,444,317 formal mode tuples **per point**, before child evaluation.
Literal source parameters are larger still. Reducing this number is not a
permitted silent substitution in the source executor.

`source_qualified`, `executable_refinement_proven` and `complexity_proven` all
remain false. This does not prove the paper, establish universal executable
refinement, certify polynomial space, show a speedup or break ETH. Resource
exhaustion returns `INCONCLUSIVE_RESOURCE_LIMIT` without a result. Unpruned source two-level
completion, large-input quantitative hashing, literal source recursion and a
portable full recursive certificate remain separate open work.

## Stronger child-contraction replay

`scripts/validate_manuscript_full_children.py` captures every one of the 76,960
child contraction values losslessly as 222 runs. Its separate oracle enumerates
weighted compositions recursively, reconstructs each one-wire group's value
from its original row/column table and rational Cauchy polynomial, and checks
all child values in order as well as every interpolation point and the root.
It does not call production packet entries, modes or child constructors.

```sh
PYTHONPATH=src python scripts/validate_manuscript_full_children.py --output-dir /outside/checkout/evidence
PYTHONPATH=src python scripts/validate_manuscript_full_children.py --replay /outside/checkout/evidence/full_children_certificate.json
```

This stronger transcript closes the aggregate-only child-value limitation for
this particular one-wire, one-active-level fixture. It remains fixture-specific,
not an arbitrary-network certificate, entry-by-entry proof, multiple shrinking
levels, or a source-qualified run. Run-length encoding is only transport; replay
recomputes the numerical values and does not trust a content hash.

## Independent review and second topology

Devin's read-only review independently checked the local Hermite functional,
precision sufficiency and child-oracle case analysis. Its report identified an
unchecked `report.parameters` block; replay now pins that block and rejects
Boolean values substituted for integer metadata. Empty scaled roots now report a
direct leaf route rather than claiming recursive execution.

A second connected two-wire finite topology has two occupied packets and a
multi-port tensor. Its complete weighted-mode point sums are compared against
independent rational half-edge enumeration at all six nonzero nodes for L=4,
including valuation-one nodes ±2. These are additional point-identity checks,
not a claim of completed two-level recovery.

A suspected kernel-denominator failure is excluded for targeted modes by the
packet orientation invariant: row group = pair[bit_i(x)], and mode target =
pair[bit_i(y0)]. Their equality implies bit_i(x) = bit_i(y0). Since v₂(t)=i,
`t-y0+x` is nonzero and has valuation at most i. The regression checks every
such x, y0 and nonzero t for L=2,4,8,16 against the actual kernel. This does not
remove any mode or weaken the kernel's invalid-crossing checks.

## Completed two-level certified-zero experiment

`scripts/validate_manuscript_certified_two_level.py` is a separate experimental
traversal, not a replacement for the unpruned source or scaled executor. It keeps
the full four-packet geometry and original canonical entry semantics, but uses a
checked partition of the formal beta domain instead of enumerating zero terms.
Its preconditions require exactly one wire, a=1, radix 2, all row labels zero,
all column labels one, the complete expected packet inventory, and the occupied
wire at slot zero. Other geometry is refused.

The only retained tuples are beta=0 and beta=e0. Every other tuple falls into
one of three zero families:

1. A positive exponent in another channel has an empty source.
2. A positive geometric exponent in the occupied channel evaluates j^b at j=0.
3. Power at least two of the remaining mode exceeds the single affine target
   row's degree.

These conditions cover the entire omitted domain independently of tensor values.
The replay reconstructs all inherited canonical tensor tables and child tables
itself, checks every leaf/point/recovered result using separate extension
arithmetic, and checks domain counts via binomial convolution. It does not call
production packing, entry, child or recovery functions. Adversarial tests disable
those producer dependencies during replay, tamper with coverage and nested
results, check geometry refusal, compare every omitted term with the unpruned
children at small precisions, and replay eight independently seeded input tables.

For the stated polynomial fixture, both source-component and installed-component
runs complete two active levels, 1,057 nodes, 264 points, 1,024 leaves and 33
recovered active nodes. The answer is again 1 + 3V modulo 4 and V². Zero-family
coverage accounts for 117,806,400 omitted formal tuples at the executed points.

```sh
PYTHONPATH=src python scripts/validate_manuscript_certified_two_level.py --output-dir /outside/checkout/two-level
PYTHONPATH=src python scripts/validate_manuscript_certified_two_level.py --replay /outside/checkout/two-level/certified_two_level.json
```

This closes a finite nested canonical-entry test, not the literal source gate.
`full_formal_domain_enumerated` is explicitly false. The unpruned two-level
traversal is still not completed: it requires 566,466,234,880 grandchild calls for
this fixture. The new certificate is limited to this one-wire geometry, not an
arbitrary-network optimizer, shrinking-child proof or general ETH solver. All
source, executable-refinement and complexity qualifications remain false.

## Connected two-level replay and tiny CNF pipeline

`validate_manuscript_connected_two_level.py` generalizes the separate zero-family
experiment to checked L=B=2 packet geometry. The complete padded inventory,
vertex labels, slot uniqueness, wire coverage and endpoint orientation are
checked before applying the reduction. Only binary b=0 modes at occupied
cross-group slots can survive. Positive geometric exponents have j=0 at their
source, missing slots have zero source, and powers above one exceed the single
target row. The retained domain still enforces total weight < p. This is an
explicit alternative finite experiment, not a silent change to the unpruned
source executor.

The connected two-wire fixture has a nonseparable degree-two row tensor and two
column tensors. Its direct integer jet is `25 + 74V`, hence `1 + 2V` modulo four.
Two active levels complete with 3,193 nodes, 798 interpolation points, 3,136 direct
leaves and 57 recovered active nodes. The child wire counts include 1, 2 and 3;
children do not satisfy the manuscript shrinking bound. The local precision
chain includes 2, 18, 25 and 43. At executed points the certified zero families
cover 44,865,517,886,504 formal tuples. This is a finite coverage count, not a
claim about general runtime or complexity.

Independent replay reconstructs every child tensor table at its creation
precision and carries inherited canonical tables separately when precision
increases. It verifies all leaf contractions, all half-edge point sums, all
recovered nodes and the integer root. Packet addresses are rederived from the
recorded labels rather than trusted. The checker verifies valid finite packing,
not optimality of the label-selection algorithm. A rational monomial linear
system independently derives the Hermite functional and required precision
loss, instead of the producer's reciprocal-series recurrence. Replay imports no
production tensor constructor, child evaluator, packing, interpolation or
recovery implementation.

Additional tests use a connected four-wire K2,2 cycle, including both occupied
orientations of one active packet. Every retained child entry is checked against
the independent table oracle. Every omitted beta at p=2,3,4 is evaluated against
the original unpruned child construction and shown to vanish; the full point sum
also agrees with the rational half-edge oracle. These cycle checks are point and
child-entry tests, not a claim that its two-level traversal was completed.

`validate_manuscript_tiny_cnf.py` adds an input-to-result demonstration: n=2,
formula `(x1 OR x2)`, truth-table tensor conversion, both active levels, complete
recursive replay and an independent original-variable SAT oracle. It returns
exact count **3**, matching all three satisfying assignments. The input adapter
is capped at n=2 and 2..3 literal occurrences with connected incidence. Exact
counts that do not fit modulo four are refused as ambiguous, never reported as
zero. This adapter does not replace any public solver or claim a general #SAT
algorithm.

```sh
PYTHONPATH=src python scripts/validate_manuscript_connected_two_level.py --output-dir /outside/checkout/connected
PYTHONPATH=src python scripts/validate_manuscript_tiny_cnf.py --output-dir /outside/checkout/tiny-cnf
```

The new milestones close finite connected two-level and tiny-input pipeline
checks for these stated experiments. They do not close the literal unpruned
source-active schedule, arbitrary-network recursive certificate, shrinking-child
bound, large-input quantitative hashing, universal executable refinement or
asymptotic complexity gates. All corresponding qualification flags stay false.

## Exact distinct-parity-row experiment

The general dispatcher already implements normalization, bounded direct cases,
unit propagation, sparsification, Tanner parity checks, greedy hash rows and
sparse-polynomial counting. Its literal ordered-list greedy search is currently
impractical even for a simple n=20 input. For `[[1,2],[3,-4]]`, B=514 and mu=2 give
P=21,135,680,000. The search domain is `4^P` ordered lists per round and 60 rounds.
The CLI's default 10,000,000 instrumented-work-unit allowance refuses this at a
preflight lower-bound check, after 69 charged units. This is a configurable
program resource budget, not a safety restriction. Raising it does not remove
the astronomical duplication.

`validate_manuscript_hash_quotient.py` tests an exact alternative enumeration.
Each list contributes only its m-bit parity row. Its attainable rows are exactly
those of Hamming weight at most P. The earliest list for a row consists of zero
padding followed by its increasing selected odd codes. Enumerating increasing
weight and lexicographic subsets therefore preserves both the score minimum and
first-minimum tie behavior. Forty tests include exhaustive original-list order
checks for m=1..4 and P=0..4 with random tied scores.

A second exact reduction removes variables absent from a sparse equation system,
renames its active variables and multiplies the result by 2^unused. Together the
reductions let this n=20 example complete with count **589,824**. Independent
replay checks all 240 candidate scores, all 60 selections, the original P and B,
the q=1 initial parity checks and the original CNF truth count. The input has four
relevant variables and sixteen unused ones. Four distinct rows replace the
repeated-list enumeration in each round; no operational cap is increased.

The driver temporarily substitutes these functions during the real general
counting dispatcher and restores them afterward. Package source and the public
CLI default are unchanged at this milestone. The independent checker covers a
single unsplit sparse leaf with the stated bounds, not arbitrary sparsification
or paper-scale expanders. This path uses exact support counting, not active
recursive tensor contraction; its contraction call count is zero. No general
runtime, source qualification or ETH claim follows.

## Public optimized counting route

The reviewed reductions are now available through explicit package calls:

```sh
veritas-manuscript count-optimized --n 20 --clauses-json '[[1,2],[3,-4]]'
```

This returns exact count 589,824 under the unchanged default work allowance.
`optimizations.count_optimized` accepts the same Formula inputs and operational
limits as the original `cnf.count`. It follows the same general dispatcher and
sparsification/Tanner parameters, substitutes only distinct parity-row search
and exact unused-variable factoring, and labels the optimization policy.
The original `count` command retains its ordered-list reference behavior.
No global module substitution is used by the public implementation.

The independent hash replay driver can exercise this API with `--integrated`.
Both API and CLI retain fail-closed resource outcomes. Distinct search is still
exponential in the clause count in general, and support factoring helps only
when variables are absent from a query. Inputs involving all variables or large
numbers of distinct rows may remain impractical. No source/refinement/complexity
qualification is enabled.

The optimized producer now reuses a further exact fixed point. Once a complete
greedy round selects zero, its added parity equation is identically zero. All
future candidate scores and first-minimum choices stay the same. The producer
keeps all 3n rows and all score values, while avoiding repeated query evaluation.
The independent checker still recomputes every score from original literals;
it does not trust the shortcut. A runtime guard pins the zero-equation premise.
Immutable snapshots prevent callback mutation from corrupting later traces,
and reuse still charges row/trace allocation and work/time checks.

With this optimization the n=20 five-clause example
`[[1,2],[3,-4],[-5,6],[7,8],[9,-10]]` returns exact count 248,832 under the default
10,000,000-unit budget. Its 60-round transcript contains all 1,920 candidate
scores and is independently replayed. The earlier checkpoint required a
100,000,000-unit allowance on the same case. These are finite measured work
counts, not a general running-time or asymptotic claim.

## Four-slot support extension

`certified_modes.DegreeCertifiedDomain` is an explicit finite alternative to the
full formal-domain iterator. It validates the complete padded inventory and
canonical addresses for supplied labels, then excludes only three provably
zero families from `eq:tensor-mode-expansion` and `eq:tensor-mode-budget`:

1. A positive mode whose source tile has no real column.
2. A positive geometric exponent b whose matching source indices j are all zero.
3. A tuple whose total selected powers for one packet and target group exceed
   the number of affine target-row factors. This cap is per group, not per tile.

Retained vectors still have the original full formal shape, original weights
and original precision bound. The filter may retain further zeros. An optional
bounded cache reuses exact kernel scalars within one immutable creation point;
no values cross a precision, polynomial, interpolation point, or budget context.
The original unpruned reference domain does not use this cache or filter.

`validate_manuscript_four_slot.py` exercises a=2, u=2, radix two, L=4, one active
level and the complete original Hermite node/multiplicity schedule. A fixed
column alphabet permutation on coordinate zero gives two parallel wires copy
slots 0 and 2 in packet ((0,1),(0,0)). Both original degree-two tensors are
nonseparable. The finite precision policy remains the separately documented
exact Hermite functional loss: p=35 at odd nodes and p=9 at even nodes. All six
nodes -3,-2,-1,1,2,3 and all 15 interpolation points per node are included.

The candidate run independently checked 38,940 child contractions, 90 points
and the root against the integer jet 13+24V. It includes 12,530 nonzero tuple
contributions involving b>0 and 840 with a power above one. Thus the earlier
L=2 binary-only support shortcut would be wrong here. The independent replay
uses rational Cauchy polynomials, a separate extension-ring implementation,
dictionary coefficient multiplication, direct Boolean half-edge sums and a
30-condition rational linear solve for the Hermite functional. The driver uses
an explicit 1,000,000,000-unit, 600-second development budget. This is a finite
cost measurement, not a speed or complexity claim.

In this end-to-end fixture the occupied packet is local at coordinate one:
its even-node domain retains only zero. Separate tests use genuinely occupied
coordinate-one modes, a target power of two on a single tile, and eight-slot
source indices j=2,3. Those are component tests, not an L=8 recovery or a second
L=4 active level. The replay also independently derives every direction and copy-index packet
address from the recorded layout. Validation status and the exact source pin
are recorded externally. All qualification flags remain false and bit operations
remain uninstrumented.

## Shared CNF encoder and explicit finite recursive count

`experimental.count_scaled_cnf` now connects the existing general `cnf.encode`
equality-tree/subdivision encoding to the same recursive executor. It does not
use the earlier tiny fixture's hand-built incidence network. Precision is n+1,
so the count on all declared variables has a unique representative, including
unused-variable factors. The field degree is 4 ceil(log2 s), with the finite
admission size s chosen by `contract_scaled`; no fixed polynomial/degree from a
small fixture is substituted. One cooperative budget covers normalization,
encoding, recursive work and count recovery. There is no hidden direct-count
fallback when the requested recursive path runs out of resources.

The original reference commands and unpruned domain remain unchanged. New CLI
commands expose two deliberately distinct choices:

```sh
veritas-manuscript count-fixed-density --n 2 --clauses-json '[[1,2]]'
veritas-manuscript count-scaled --n 2 --clauses-json '[[1,2]]' --a 1 --u 1 --radix 2 --active-depth 2 --column-shift 1 --mode-policy certified --max-work 2000000000 --max-seconds 600
```

The first exposes the existing fixed-density branch, which can use the source
finite direct range. The second requires every finite schedule setting and the
choice of full or certified mode domain explicitly. The certified option uses
the general source-tile/target-degree zero rules above. It does not assert that
the full formal domain was enumerated. Finite depth and local precision remain
experimental; neither command enables source, refinement or complexity claims.

The package API imposes no n=2 or fixed occurrence limit. Resource caps still
apply. The separate `validate_manuscript_scaled_cnf.py` checker is intentionally
bounded to at most 12 original variables, 8 wires at each recursive node, field
degree 16, precision 256, 200,000 events, binary one-coordinate geometry and
scalar jets. These limits belong to this independent oracle, not the producer.
It independently proves the root encoding equivalence by equality components,
checks all original literal signs and unused variables, derives the field and
finite admission parameters, rebuilds canonical packet addresses and every
child table, verifies all leaf/recovered contractions by Boolean sums and all
interpolation points by half-edge sums, and compares the root count with the
original CNF truth table. It does not call the producer's encoder, child builder,
entry evaluator or recovery routine during replay.

The four-wire n=2 clause `(x1 OR x2)` development run uses two active levels,
43,473 recursive calls, 5,434 interpolation points and 21,736 retained exponent
tuples. It returns count 3 at precision 3. It charges 1,696,466,773 cooperative
work units with the explicit 2-billion-unit allowance above. A 1-billion-unit
probe refused without a count. This larger allowance is not the default CLI
budget and does not establish an improvement in speed. Sealed validation and
replay results are recorded in the external evidence directory.

All four count commands now validate the JSON container and literal types
before constructing a Formula. A Boolean, fractional value, string or object
is rejected rather than silently cast into a different formula. Malformed
JSON and DIMACS produce clean argument errors instead of counts or tracebacks.

## Sparse-query bounded degree exceptions

The general sparse-query construction now checks the degree admission of every
formal degree array before evaluating a tensor branch. A finite n=20 example
with nine repeated parity equations on all twenty variables admits an array
with 54 indexed wires at one vertex, while its fixed source size s=60 permits
degree at most 40. Previously this latent path raised ValueError if resource
limits did not stop an earlier array. No incorrect completed count was observed.

The new preflight computes the exact maximum indexed degree for each row and
column group, under the original total incidence-degree cap K. It uses a
budgeted knapsack of the widths ceil(log2 binom(N,d)). Choices above N/2 can be
replaced by N-d without changing the width and with no larger degree cost.
The calculation uses integer arithmetic and at-most-K counters, not a floating
approximation or an exponential enumeration of the full array grid. A
maximizing choice at one vertex extends to a valid formal array by putting zero
at every other pair. This certifies admission for all arrays or finds a genuine
formal-array degree exception. It does not certify that the offending term has
a nonzero coefficient.

For an exceptional branch, the implementation follows the bounded-size direct
enumeration allowance at the end of `lem:tensor-sparse-query`. It counts the
original already-substituted equations over every remaining free variable,
including variables absent from the equations. It does not enumerate the much
larger indexed-wire network, add a partial tensor sum, discard an array, or
multiply by the number of fixed heavy-variable assignments. All branches are
still disjoint, and all work uses the same cooperative budget. Exhaustion after
any branch discards the partial total and returns no count.

The receipt uses `SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT` and records the
number of fallback branches, the largest exact grouped degree and the unchanged source
limit. Pure contraction retains `SPARSE_POLY_CONTRACT`. Unused-variable factoring
preserves the inner route and degree-exception diagnostics. Sparse hash wrappers
retain the final query diagnostics, and the general dispatcher summarizes final
query fallback branches/leaves. That summary explicitly excludes greedy scoring
queries. The outer hash/sparsification labels do not assert that every common-zero
query used tensor contraction. `count-scaled` is separate and
continues to forbid a direct-CNF fallback.

The n=20 example completes with 524,288 zeros; adding one hundred repeated x0=0
equations exercises heavy-variable substitution and gives 262,144 zeros. The
development runs charged about 211M and 100M units under explicit 500M/300-second
allowances. Their independent checker counts the original Boolean assignments
and checks the degree maxima by composition search, not the producer knapsack.
These are explicit finite direct-branch results, not new recursive evidence,
normal-budget results, a general speed guarantee or an asymptotic claim. For
large free-variable sets the direct branch can still exhaust its budget.

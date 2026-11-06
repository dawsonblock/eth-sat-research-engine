# Child-shrink theorem: proof, implementation, and verification plan

## Executive result

The six-edge child from the eight-edge finite run is explained by a failed
parameter regime, not by a counterexample to the manuscript's packing lemma.
Its finite parameters do not satisfy the lemma's preconditions. The exact
mathematical implication needed for shrinking is straightforward once a
packing has the required port bound:

> If every group has at most `3M/r` row-side ports and `3M/r` column-side
> ports, and the child has exactly one Boolean wire per such port, then every
> child has at most `6M/r` wires. For `r=64`, this is `3M/32 < M/8`.

The hard work is to establish, construct, and preserve those port bounds at
every active recursive call, and then charge every mode, child, interpolation,
entry evaluation, bit operation, and leaf. This document gives the proof
obligations and implementation sequence. It does not claim that the current
Python engine has met them, independently verifies the cited manuscript, or
proves `P = NP`.

The construction below is pinned to OpenAI/math commit
[`4eaee87548250b2682affda7d05d947c05554bae`](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex).
That source is a research manuscript. Its proof claims and hypotheses must be
treated as the specification to reproduce and review, not as evidence that
this repository already implements its algorithm.

## 1. Define the supported theorem contract

The theorem-mode input is not arbitrary Python tensor code. It must be a
finite, explicitly described bipartite Boolean tensor network with:

- `M` Boolean wires, represented by an explicit bipartite multigraph;
- maximum row/column vertex degree at most the declared `Delta`;
- immutable, deterministic tensor-entry recipes and a declared creation
  precision for every tensor created by recursion;
- entry evaluators with a proved time, space, and output-bit bound;
- a fixed coefficient ring, extension polynomial, target precision, and
  interpolation schedule for the entire ancestry;
- a size parameter `s`, input-description bit length `L_in`, root bound
  `M_0 <= C s`, and the manuscript's hypotheses on `s`, degrees, and entries.

Every recursive node carries the original immutable recipe, its creation-time
precision, its parent-certificate digest, its exact parameter-schedule index,
and the proof data needed to replay its construction. A residue evaluated at a
higher precision is not defined by canonical lifting alone: the recipe must
be reevaluated or the manuscript's precise lift lemma must apply.

The API has two explicitly distinct modes:

| Mode | Allowed scope | Failure behavior |
|---|---|---|
| `finite` | Small, scaled experiments and bounded exact leaves | May return an exact finite result; labels any fallback and all observed costs |
| `theorem` | Only inputs satisfying the pinned construction's complete hypotheses | Rejects unsupported input before claiming a result; no arbitrary large direct-enumeration fallback |

An implementation budget can stop execution and return `INCONCLUSIVE_RESOURCE_LIMIT`
with no count. In a theorem proof, the supported-input preconditions and
correctness proof must ensure that the algorithm itself terminates with the
claimed bound; a resource limit is not a mathematical fallback.

## 2. The child-size lemma and proof

Let `G` be a bipartite multigraph with `M` edges. The packet labels assign
each row vertex and each column vertex a word in `[r]^a`. At one coordinate,
let `R_g` be the number of parent row-side edge ports assigned symbol `g`, and
`C_g` the number of parent column-side ports assigned `g`.

The child representation used by the construction makes two half-wire
variables for each parent edge `e`: a row half-wire `Y_e` and a column
half-wire `X_e`. Each is assigned to exactly one group. Packet factors attach
to those half-wires but do not create additional Boolean wire variables.
Consequently, for each group `g`,

\[
  M_g = R_g + C_g.
\]

If the packing guarantees `R_g <= 3M/r` and `C_g <= 3M/r` for every `g`,
then, separately for every child,

\[
  M_g <= 6M/r.
\]

Setting `r=64` gives

\[
  M_g <= 6M/64 = 3M/32 < M/8.
\]

This is a uniform-per-child result, not an average-load result. Summing all
child sizes (`sum_g M_g = 2M`) is a useful accounting invariant but does not
by itself imply any child is small. The port bound is the premise that does
the work.

### Why the eight-edge witness does not meet this lemma

The recorded finite witness has `M=8`, `r=4`, `a=1`, `D=16`, `L=2`,
`H_pad=2`, and maximum side degree `Delta=1`. Its group child sizes are
`6, 6, 2, 2`; the largest has ratio `6/8 = 3/4`. For this input,

| D.3 numerical condition | Required | Observed | Result |
|---|---:|---:|---|
| `M >= 2 D^2 Delta` | `512` | `8` | fails |
| `M >= L D` | `32` | `8` | fails |
| `2L <= Delta` | `4 <= 1` | false | fails |
| `D H_pad <= 3M` | `32 <= 24` | false | fails |

At `M=8`, the proposed `M_child <= 3M/32` bound requires an integer child
size of zero. This emphasizes that the asymptotic active construction is not
supposed to run on this tiny finite schedule. The example diagnoses the
finite parameter choice; it does not refute a lemma whose hypotheses are
false on the example.

The finite child audit is useful for checking the current wire convention,
half-wire partition, packet ports, and this specific failure. It cannot
establish uniform shrinkage for all eligible graphs or recursive calls.

The gap is not specific to `M=8`. Under the displayed D.3 sufficient
conditions with `r=64` and `a>=1`, `L>=2`, `D=r^(2a)>=4096`, and
`Delta>=2L>=4`. Hence every call using those conditions must have
`M>=2 D^2 Delta>=134,217,728`. This is a consequence of this particular
sufficient parameter regime, not a lower bound on every possible exact
construction. The actual depth schedule can impose stronger requirements.
The current finite constructor's active-wire cap is far below this regime;
successfully checking its children therefore cannot establish theorem
applicability.

## 3. Construct and certify the deterministic packing

The pinned Appendix D.3 construction supplies the required port premise.
The following is the proof shape to formalize and refine into code.

Let `a >= 1`, `L=2^a`, and `D=r^(2a)`. Independently assign each vertex a
uniform label in `[r]^a`. For each directed pair label `gamma`, let `X_gamma`
be the number of edges in that class, and define

\[
  \Phi = \sum_\gamma (X_\gamma-M/D)^2.
\]

Expand the square and take expectation over labels. For ordered edge pairs
with four distinct endpoints, the probability that their directed labels
agree is `1/D`, so their contribution to `E[Phi]` is zero. There are at most
`2M Delta` ordered edge pairs sharing an endpoint; each such contribution is
at most one. Therefore

\[
  \mathbb E[\Phi] <= 2M\Delta.
\]

Fix labels one coordinate at a time by conditional expectation. For each
unassigned vertex-coordinate, evaluate the exact conditional expectation
under each of the `r` possible symbols and choose a minimum. The average of
these choices is the current conditional expectation, so this deterministic
choice never increases it. When all labels are fixed,

\[
  \Phi <= 2M\Delta,
  \qquad
  X_\gamma <= M/D + \sqrt{2M\Delta}\quad\text{for every }\gamma.
\]

Round the maximum class size upward to a multiple of `L`, obtaining
`H_pad <= M/D + sqrt(2M Delta) + L`. Under
`M >= 2D^2 Delta`, `sqrt(2M Delta) <= M/D`; under `M >= LD`,
`L <= M/D`. Thus

\[
  H_{pad} <= 3M/D.
\]

Pad every directed class to `H_pad` and use the manuscript's orientation
slots to partition them into packets of `L=2^a` slots. Concretely, fix the
unordered pair of endpoint symbols in each of the `a` coordinates. Let `q`
be the number of coordinates where the two symbols differ. A packet has one
slot for each `a`-bit word: bits in the `q` differing coordinates choose the
orientation and therefore one of the `2^q` directed classes; bits in the
other `a-q` coordinates choose one of `2^(a-q)` copies from that class. Each
directed class therefore contributes `2^(a-q)` slots to a packet. Across
`2^q` orientations this fills exactly `2^a=L` slots. Since `H_pad` is a
multiple of `L`, the padded occurrences of each class can be partitioned
across these packet slots without a remainder. Thus every padded class slot
is used exactly once. For a fixed coordinate, side, and symbol,
exactly `D/r` directed labels carry that symbol on that side. Hence its real
port load is at most

\[
  H_{pad}D/r <= 3M/r.
\]

The number of packets is at most `H_pad D/L <= 3M/L`. The separate
`2L <= Delta` condition is used for the new packet-vertex degree bound; it is
not needed for the potential or port calculation itself.

### Implementation requirements for this lemma

1. Implement the fixed-label conditional-expectation procedure using exact
   rational/integer comparisons. Document a canonical tie-break so output is
   deterministic.
2. Compute conditional collision probabilities directly from the partial
   labels. Check the formula independently against exhaustive labelings on
   tiny multigraphs.
3. Store packets implicitly. A slot query must derive the packet, orientation,
   directed class, and real/padded edge without allocating all `D` classes.
4. Replay-check every real edge's unique slot, endpoint agreement, orientation,
   padding, packet count, per-side symbol loads, maximum vertex degree, and
   child wire count. Check the labeling trace against the canonical
   conditional-expectation decisions, not only the final claimed loads.
5. Use Python arbitrary-precision integers/rationals in the finite
   implementation; a theorem implementation still needs a bit-operation
   proof for the sizes of those quantities. A bounded constructor that rejects
   `D > 4096` is not a theorem-scale constructor.

## 4. Schedule and induction across all recursive calls

Pin and implement the manuscript's exact schedule with integer arithmetic.
The repository's current audit records the following candidate schedule:

\[
\lambda=\lceil\log_2 s\rceil,\quad
\Delta=\lceil s^{9/10}\rceil,\quad
\epsilon=2^{-17},\quad r=64,\quad
H=\left\lceil\frac{s}{\lfloor\sqrt\lambda\rfloor}\right\rceil,
\]

\[
u_d=\left\lfloor\frac{\epsilon\lambda}{2^d}\right\rfloor,
\quad a_d=2\sum_{j=0}^{d}u_j,\quad
L_d=2^{a_d},\quad D_d=r^{2a_d}.
\]

The active branch is used only when `M_d > H`. The numeric preflight must
check at every active depth the applicable inequalities, including
`M_d >= 2D_d^2 Delta`, `M_d >= L_d D_d`, and `2L_d <= Delta`, along with
integer floors, extension/ring requirements, degree invariants, and entry
recipe assumptions. It must also establish the root and ancestry invariants
used to bound `M_d`.

An existing deliberately loose sufficient threshold in
[`APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md`](APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md)
is conditional on `M_0 <= C s`, `M_{d+1} <= M_d/8`, and the degree bound. It
is an asymptotic numerical argument, not a practical operating threshold and
not evidence the current bounded constructor can execute at those values.
The finite range below a fixed threshold can be treated as a base case in a
mathematical algorithm, but that enormous constant must be stated honestly.

The uniform induction must prove, for every active node and every child:

- the parent satisfies the D.3 schedule hypotheses;
- deterministic packing succeeds and has the certified port bounds;
- all child descriptions are exactly the ones covered by the construction;
- every child has `M_{d+1} <= 3M_d/32`;
- old degrees remain bounded and new packet vertices have degree at most
  `2L_d <= Delta`;
- the next schedule's precision, degree, field, and entry hypotheses hold;
- the leaf branch is taken only at `M <= H`.

In theorem mode, a non-shrinking or malformed child is a violated invariant,
not permission to enumerate a large child. The implementation must fail
closed; the mathematical proof must establish that this state is unreachable
for every covered input.

## 5. Exactness: deformation, modes, pruning, and reconstruction

Child size alone is insufficient. For each active node, prove and implement
the entire value identity:

1. **Cauchy wire deformation.** For
   `S={-L,...,L-1}`, `C(T)=prod_{q in S}(T-q)`, and
   `x,y in {0,...,L-1}`, define
   `W_xy(T)=C(T)/(C'(0)(T-(y-x)))`. The factor cancels, so this is a
   polynomial; directly show `W(0)=I` and thus the deformed contraction agrees
   with the original at zero. The normalized coefficients are rational in
   general. The implementation must use the manuscript's exact scaled
   coefficient/precision construction; it must not reduce `C'(0)` modulo
   `2^p` and attempt to invert it when it is a nonunit.
2. **Mode expansion.** Expand each deformed packet interaction into the
   manuscript's exact weighted modes. Certificates include node, group,
   packet/slot, coefficient recipe, weight, valuation lower bound, coefficient
   ring, and creation precision.
3. **Valuation and cutoff.** If a mode coefficient is divisible by `2^w`,
   its `beta`th power is divisible by `2^(w beta)`. Modulo `2^p`, every tuple
   with `sum_i w_i beta_i >= p` vanishes. Only those tuples with strict weight
   sum `< p` are evaluated. The implementation checker must verify the actual
   coefficient is in the claimed ideal; a declared weight is not evidence.
4. **Factorization.** For each retained tuple, establish that its coefficient
   factors into the specified group-local child contractions. Verify the
   parent-to-children identity symbolically for tiny cases and with an
   independent exact oracle for finite tests.
5. **Interpolation/recovery.** Compute all prescribed Hermite jets at the
   correct extension-field points and mixed 2-adic precisions. Reconstruct
   only the required coefficients with exact common-denominator/integer
   arithmetic; never divide by a nonunit modulo `2^p`. Bind each coefficient
   to its creation precision and prove every reconstruction input has enough
   guard bits.
6. **Root count.** For a count-preserving reduction from a CNF with `n`
   declared variables, the count is at most `2^n`; a verified residue modulo
   `2^(n+1)` determines it. This recovers the integer only after the exact
   contraction and reduction correspondence have been established.

Finite exhaustive comparison tests can falsify these identities on small
inputs. They do not replace the uniform algebraic proofs.

## 6. Close the whole runtime and space recurrence

Let `B_d` include **all** recursive child calls generated by a node at depth
`d`: retained weighted tuples, all groups, all interpolation points and all
Hermite jets. Do not treat a tuple bound as the total branching factor.
Let `A_d` include packing, mode generation, tuple iteration, child creation,
entry evaluation, interpolation, reconstruction, and bit arithmetic at that
node. For each node, the executed work is bounded by

\[
T(M_d,d) <= A_d + \sum_{j=1}^{B_d} T(M_{d+1,j},d+1).
\]

The proof target is a uniform bound under the manuscript's supported
description and entry-evaluation hypotheses, not a fit to benchmark data. The
current conditional recurrence note derives the desired asymptotic conclusion
if all these assumptions hold. In particular, with `rho=3/32`,
`M_d <= C s rho^d`, and `u_d >= c lambda/2^d`,

\[
\sum_d M_d/\sqrt{u_d}
<= O(s/\sqrt\lambda)\sum_d(\rho\sqrt2)^d
= O(s/\sqrt{\log s}),
\]

because `rho sqrt(2) < 1`. This is only one component of the proof. The
branching bound must already include the 64 groups and interpolation
multiplicity, and the local bit work must include all construction and exact
arithmetic overhead. See
[`APPENDIX_D_RECURSION_TREE_LEMMA.md`](APPENDIX_D_RECURSION_TREE_LEMMA.md)
for the full conditional recurrence assumptions.

Charge explicitly:

- conditional-expectation packing and implicit slot lookup;
- mode coefficient generation, coefficient bit lengths, valuation checks;
- streamed weighted-tuple enumeration and child recipe construction;
- each recursive call, interpolation point, jet coefficient, and group;
- entry evaluation, multiplication/addition bit costs, precision lifts;
- Hermite reconstruction denominators and numerator bit lengths;
- exact leaf work and leaf entry evaluations;
- retained descriptions, interpolation accumulators, tuple state, recursion
  stack, and peak live memory.

For polynomial space, prove that one node, one tuple, and one child are
processed at a time; discard completed child state; recompute entries from
polynomial-size recipes; and retain no exponential packet, mode, tuple, or
child cache. Depth-first execution alone is not enough if any single frame or
intermediate table has super-polynomial bit size.

## 7. Concrete implementation sequence and acceptance gates

### Phase A — Freeze specification and evidence

- Record the exact manuscript commit, theorem/appendix section, field and
  ring conventions, network encoding, size/degree/entry hypotheses, schedule,
  and leaf rule in machine-readable configuration.
- Make theorem mode reject unsupported inputs before allocating large state.
- Preserve finite experiments as explicitly finite; no finite pass upgrades
  theorem compliance.

**Gate:** A schedule checker independently recomputes every integer
parameter and rejects one-bit changes, invalid floors, insufficient
precision, and unsupported tensor recipes.

### Phase B — Replace the bounded packing bridge

- Implement exact conditional-expectation labeling for the full eligible
  theorem graph domain.
- Add lazy packet/slot/group incidence APIs; do not allocate all `D` label
  classes or padded slots.
- Extend the checker to replay labels, tie-breaks, edge-to-slot bijection,
  padding, orientation, packet count, port loads, and degree bounds.
- Keep the current `D<=4096` constructor available only as a finite reference.

**Gate:** Implicit and explicit constructions agree on small instances;
altered label, trace, slot, orientation, padding, or port bound is rejected;
memory scales with graph description and a slot query, not all possible
classes.

### Phase C — Certify exact children and shrinking

- Construct child descriptions directly from packet slot references and
  parent half-wires.
- Independently count child Boolean wires and all tensor ports.
- Verify every old factor's port map, every packet factor's port map, degree,
  creation precision, and provenance hash.
- Apply the `6M/r` proof only after the checker verifies each side-symbol load
  is at most `3M/r`.

**Gate:** For every eligible small parent and every group, independently
replay the child identity and verify `M_child <= 6M/r`; theorem mode refuses
the eight-edge finite witness as outside the active schedule rather than
asserting or attempting the asymptotic shrink bound.

### Phase D — Implement the exact contraction identity

- Implement the Cauchy polynomial, mode stream, coefficient valuation
  witnesses, weighted tuple cutoff, and immutable child recipes.
- Add mixed-precision Hermite reconstruction with a checker for point
  distinctness, jet multiplicities, guard precision, and exact denominators.
- Keep direct oracles in a separate verification-only path, with their work
  recorded outside algorithm work.

**Gate:** Exhaustive independent parent-to-children equality on bounded
networks at two or more recursive levels; tampered coefficient, valuation,
precision, child, or interpolation certificates fail replay.

### Phase E — Complete resource accounting

- Add a whole-run ledger for node/child counts, modes by weight, retained
  tuples, ring operations, operand bit sizes, entry calls, interpolation,
  direct leaves, and peak retained objects.
- Stream modes and tuples; disable unbounded caches in theorem mode.
- Resource exhaustion returns inconclusive with no count.

**Gate:** On reproducible runs, the ledger reconciles with instrumented
operations; it labels theoretical upper bounds separately from observed
operations and wall time. The independent oracle is reported separately.

### Phase F — Prove uniformity and independently review

- Prove schedule applicability for every active descendant, not a single
  generated packing.
- Prove conditional-expectation packing, exact packet factorization, mode
  valuation, weighted tuple count, child size/degree, creation-time precision,
  reconstruction, and entry-cost invariants.
- Prove the complete recursion-tree bit-work recurrence and polynomial-space
  bound separately.
- Formalize executable invariants and the elementary algebra/packing lemmas
  in Lean or another proof assistant; obtain review of the manuscript-to-code
  correspondence by someone independent of this implementation.

**Gate:** One reviewable proof covers all inputs in the declared theorem
contract. Tests and finite certificates remain engineering evidence, not the
uniform theorem.

## 8. Current status and immediate next work

The repository currently has a bounded `tapered_v4` experimental recursor,
finite child-size certificates, and manuscript-audit notes. The implementation
has now been extended with a sparse occupied-slot packet source, which avoids
allocating the `L`-slot padded array for each occupied packet. The v4 recursor,
point-mode validator, and child builder consume this source directly. The D.3
checker can replay the deterministic labeling trace, and a per-coordinate
audit reports every group’s row/column half-wire counts. An optional
preconditioned constructor checks the D.3 numeric hypotheses before building
and replaying a radix-64 packing for one graph.

These are finite implementation results. The recursor still does not
implement theorem mode; the geometric mode builder remains limited to small
parents and scaled parameters, interpolation and precision are bounded, and
the whole-run bit-work and memory ledger is incomplete. The eight-edge audit
remains `FINITE_EXPERIMENT_ONLY`. The new preconditioned constructor has no
finite successful radix-64 case in the current tests: its D.3 preconditions
are already extremely large for `a=1`.

The local child-size implication is proved above. The sparse packet/child
interface and finite replay checks are implemented, but they do not provide
the theorem-scale source-to-code refinement. The next code milestone is to
replace the bounded geometric mode builder with the complete source
construction at the prescribed tapered points, keeping the sparse slot
interface and immutable creation precision, then replay the parent-to-child
identity for every retained tuple.

The eight-edge example is a valid exactness experiment but cannot be used to
test the asymptotic shrink inequality: for `M=8`, its right-hand side is less
than one wire, while its finite packet schedule violates multiple hypotheses.
The correct theorem-mode behavior is to classify it under the explicitly
specified base-case/finite regime; changing its group assignment to force a
zero-wire child would not implement the theorem's construction.

The next mathematical blockers remain distinct:

1. Does the D.3 packing proof, with all stated hypotheses and boundary cases,
prove the advertised uniform per-side load and packet properties?
2. Does the actual code refine that construction with bounded bit complexity
   and without expanding implicit classes?
3. Does each recursively constructed child satisfy the exact mode identity,
   immutable precision, and degree/entry assumptions?
4. Do the mode/interpolation/leaf costs close the full bit-operation and
   polynomial-space recurrence?
5. Has an independent proof review validated the pinned manuscript and the
   implementation correspondence?

Until all five are closed, report a finite exact answer as finite evidence
only, report failed budgets as inconclusive, and make no universal
subexponential claim for this implementation. A subexponential SAT-counting
bound, even if established, is not a proof of `P = NP`.

The current source snapshot passes 710 tests, including sparse-slot mode and
child integration, deterministic trace tampering, and finite child-load
accounting. This supports the bounded implementation only; the theorem-mode
path remains explicitly unavailable.

## References in this repository

- [Pinned Appendix D quantitative contraction source](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex)
- [Packing argument and its implementation limits](APPENDIX_D_PACKING_ARGUMENT.md)
- [Proof obligations and conditional deductions](APPENDIX_D_PROOF_AUDIT_20261031.md)
- [Explicit sufficient schedule threshold](APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md)
- [Conditional recursion-tree bound](APPENDIX_D_RECURSION_TREE_LEMMA.md)
- [Finite v4 implementation and eight-wire child audit](TAPERED_V4_FOUNDATION.md)

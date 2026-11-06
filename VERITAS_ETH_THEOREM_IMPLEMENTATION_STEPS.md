VERITAS-ETH: implementation steps from the R9.3 packet model to the complete source algorithm

Prepared from the actual R9.3 checkout and pinned manuscript. This is a proposed
implementation specification, not evidence that the remaining proofs exist.
It is stored outside the sealed release so it does not invalidate its manifest.

Baseline ZIP SHA-256:
`173bb476ccf87e1f0518f5a2c4e5275e8dd570de41a2e5a7fd0a056e993c543d`.

Mathematical source: `VERITAS_ETH_R9_PACKING_STAGE/paper/quantitative-contraction.tex`,
SHA-256 `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
Also read the theorem interface and outer reductions in
`paper/quantitative-reduction.tex`. Source labels, not old Appendix-D aliases,
define the contracts.

The deliverable is one algorithm with a count-preservation proof, an explicit
executable trust boundary, and a cost proof for that same algorithm. A local
test pass, a proved Lean model, and verified native execution are separate
qualification states.

**1. Freeze the target statement and the execution architecture.**

Record the exact hypotheses of `thm:tensor-contraction`: fixed positive
constants C,A,b; integer s>=2; at most Cs edges; maximum degree at most
ceil(s^(9/10)); polynomially many vertices; 1<=P0,ell<=Cs; and tensor entry
routines satisfying the stated uniform time and space bounds. Do not replace
the entry-routine hypothesis with “a Python callback is available.”

Keep three layers: executable mathematical definitions in Lean; Python's
reference implementation and orchestration; optional exact C++ acceleration.
For each operation specify inputs, a mathematical denotation, hypotheses,
postconditions, cost model, and a sound checker or refinement theorem.

Use the whole-word sorted streaming labeler as the intended source-shaped
packing implementation. Preserve the coordinate-at-a-time builder for its
existing finite APIs. They select different labels on some inputs.

Publish separate states for MODEL_PROVED, FINITE_TESTED,
CHECKED_EXECUTION, EXECUTABLE_REFINEMENT_PROVED, and INCONCLUSIVE. A Python
boolean claiming a proof is not evidence. Ordinary Lean compilation also
leaves a compiler/runtime trust boundary; do not label it verified extraction.
An accelerated kernel may propose data which a checker validates, but the
checker must have a soundness theorem and its own executable boundary.

Gate: a source-to-code obligation register covers every transformation;
the theorem-mode guard remains in place until all required obligations close.

**2. Separate theorem state from the finite experiment state.**

Current edit sites: `tapered_v4/model.py`, `parameters.py`, `recursor.py`,
`appendix_d_schedule.py`. Introduce a separately named source context/node
representation; these names are proposed, not existing APIs.

The immutable root context must carry s,C,A,b,P0,ell, the selected extension
polynomial, the manuscript identity and graph/entry-description contracts.
Each node carries the current network, depth d, current precision p, and
immutable tensor descriptions. Compute M from the current network. Never
substitute M for s, or change s when descending. For the fixed-density CNF
reduction, the paper chooses s=n+m.

Keep finite caps intact. The existing state rejects extension degree above
eight and the current point-mode/Hermite paths have small instance caps.
Implement generic resource-admitted kernels behind the new context; inspect
dimensions and estimated allocations before constructing large objects.
Resource refusal must return INCONCLUSIVE, without a count or proof flag.

Gate: malformed root contexts, wrong s, changed extension polynomials, invalid
creation precisions, and unsupported resource demands fail deterministically.

**3. Prove the complete schedule, including its base cases.**

Implement the following using exact integer arithmetic:

```
lambda = ceil(log2(s))
e = 4*lambda
H_leaf = ceil(s / floor(sqrt(lambda)))
r = 64
Delta = ceil(s^(9/10))
u_d = floor(lambda / (131072 * 2^d))
a_d = 2 * sum(u_j for j in 0..d)
L = 2^a_d
D_arr = r^(2*a_d)
```

Use integer roots for Delta and integer shifts/division for the schedule.
Check maximum degree, the root edge bound, depth, current precision bounds,
and every active-call condition. In particular:

```
M >= 2*D_arr^2*Delta
M >= L*D_arr
2*L <= Delta
```

These three inequalities alone do not certify the source schedule. Prove
that the root hypotheses and inductive child invariants imply all the needed
parameter inequalities above a stated threshold depending only on the fixed
constants. The existing symbolic preflight is conditional evidence to extend,
not that complete proof.

Handle the source's fixed small-size range by an explicitly specified direct
algorithm. Handle recursive leaves exactly when M<=H_leaf. A failed active
proof obligation must not silently become a direct leaf. A total mathematical
algorithm needs a proved threshold/base-case coverage argument; a capped
runtime may still refuse work operationally.

Gate: exact boundary tests and Lean proofs cover floor/ceiling transitions,
positive-u active calls, leaf selection, and all recursive parameter invariants.
Tiny scaled fixtures retain a finite qualification. Positive u_0 already
requires lambda>=131072, which is necessary, not sufficient for eligibility.

**4. Close labeling correspondence and the packet-domain proof.**

Current edit sites: `eth_packing_v26/streaming.py`, `streaming_check.py`,
`packet_bijection.py`, `global_packet_address.py`, and the D3 Lean modules.

Specify the partial assignment as a finite map keyed by (side,vertex,coordinate).
Prove the relation to Lean's `PackingPartial`, including unassigned entries.
Prove the candidate sequence matches lexicographic product order. Combine
that with the proved score identity and first-minimum theorem to prove one
labeling step, then induction over the entire sorted vertex sequence.
Compare full traces; equal final objective values do not establish equal runs.

Connect the resulting labels to the existing R9.3 occurrence-rank and packet
model. Define explicit finite types for all radix-bounded directed-class
offsets and padded packet positions. Construct their equivalence, prove its
cardinality equality, and derive packet count from the actual construction.
Connect computed common padding with the conditional-expectation load bound.
Then derive the actual row and column port bounds for every coordinate/group.

The needed bounds are R_g,C_g<=3M/64. The child bound then follows as
M_g=R_g+C_g<=3M/32<M/8. Keep repeated edge occurrences indexed separately.

Gate: the general Lean construction proves assignment, inverses, cardinality,
port bounds and run semantics. The executable bridge is separately established
or explicitly remains unproved. Existing finite auditors cannot supply it.

**5. Generalize exact arithmetic without changing the represented tensors.**

Current edit sites: `eth_arithmetic/`, `math_exact/`, `creation_lifts.py`,
and the described-network/tensor-entry representations.

Use one fixed monic degree-e polynomial f, irreducible modulo two, throughout
the recursive computation. Pass f itself to every kernel; accepting only its
degree and choosing another polynomial is insufficient.

Represent A_p=(Z/2^pZ)[U,V]/(f(U),V^ell) with canonical coordinate residues.
Prove addition, multiplication, reduction, unit inversion and coefficientwise
precision relations. For rational intermediate calculations, factor powers
of two explicitly and invert only the remaining units. Reject precision loss
which is not justified by a valuation/guard argument.

Every tensor description stores creation precision p_c. Its entry at later
precision is the same canonical representative obtained by evaluating its
description modulo 2^p_c. Canonical lifting is not a ring homomorphism: do not
replace this process by reevaluation of the original expression at a new p.

Keep the ring variable V, truncated at V^ell, distinct from the Hermite
interpolation variable z. The Taylor truncation in z is a different operation.

Gate: universal ring/representation lemmas and independent rational/modular
tests agree, including invalid division and corrupted creation-lift cases.

**6. Prove and implement the complete Cauchy/mode action.**

Current edit sites: `point_modes.py`, the Cauchy modules,
`independent_r82/point_mode_oracle.py`, and `independent_r82/pruning.py`.

Construct S={-L,...,L-1}, C(T)=product(T-q), alpha=2L, and
W_xy(T)=[C(T)/(T-(y-x))]/C'(0), by polynomial cancellation before any modular
operation. Prove W(0)=I, degree bounds, and `lem:tensor-integrality`.

At each active t, let i=v2(t). Group by label coordinate i. Preserve local
entries. Partition columns by y=y0+2^(i+1)j. For every required crossing tile
and b with b+1<p_t, implement the exact coefficient

```
C(T)/(C'(0)*(T-y0+x)) * (2^(i+1)/(T-y0+x))^b
```

and mode L_Z(X)=sum(j^b X_y), with weight w_Z=b+1. Treat j^0=1 even at j=0.
Prove its coefficient is divisible by 2^(b+1) and prove the discarded geometric
remainder vanishes modulo 2^p_t. This establishes the full mode expansion,
not just the validity of the terms a generator happened to return.

Compare mathematical actions rather than arbitrary mode names, since bases
can differ. Start with the complete source domain; remove absent tiles or
target rows only with an explicit algebraic-zero argument.

Gate: a general expansion/valuation theorem, plus independent exhaustive tiny
and adversarial action tests detecting missing terms, signs, shifts, supports
and coefficients. Tests do not stand in for that theorem.

**7. Establish tuple completeness and every pruning rule.**

Current edit sites: `structural_tuples.py`, `tuple_stream_check.py`, mode
matching/checking modules, and the independent pruning oracle.

The source domain is beta>=0 with sum(w_Z*beta_Z)<p_t. Any smaller structural
domain must be proved to omit only zero contributions. Derive individual
mode capacity and joint packet/target-group row capacity from the affine
row-factor product. Keep Hall-based pruning optional until its zero-witness
soundness is proved for the actual supports.

Retain canonical strict tuple order, membership checks, and the independent
truncated generating-function count. Prove enumeration completeness and
uniqueness, not just equality of the emitted length with another counter.
For every omission, prove zero coefficient or valuation at least p_t.

Overstated valuations can wrongly discard needed terms. Understated lower
bounds generally retain extra work, but can invalidate the claimed complexity
bound. Test both effects rather than treating them as the same fault.

Gate: the unpruned mathematical expansion equals the pruned expansion;
substitution, duplicates, wrong capacities, overlap errors and boundary-weight
mutations are rejected. Unsupported premises yield INCONCLUSIVE.

**8. Build the exact 64 children and prove the contraction identity.**

Current edit sites: `point_children.py`, `lazy_children.py`, `child_recipe_check.py`,
child topology/audit modules, and tensor description types.

For each retained beta and each of all 64 groups, place every current vertex
with that group label on one side. Put the corresponding packet vertices on
the other side and retain every real incident port. For a packet-group tensor,
extract targeted beta coefficients from the product of its affine row factors,
then multiply every outgoing source form L_Z(X)^beta_Z.

Preserve zero-arity/scalar factors: an empty group is not automatically one.
A missing target row with a positive target exponent gives zero. An empty
source tile contributes one at exponent zero and zero at positive exponent.
Preserve inherited entries through their creation-time descriptions and tag
each new packet tensor with p_t.

Prove finite-sum distribution, coefficient extraction and groupwise separation
to establish `eq:tensor-recursion-identity` for every admissible point:

```
F(t+alpha*zeta) = sum_beta product_{g=0..63} contract(child_g_beta)  (mod 2^p_t).
```

Check actual child edges, not a predicted size. Apply the port theorem to
derive M_child<=3M/32, and prove old degrees are unchanged while new packet
degrees are at most 2L<=Delta. New packet entry recipes should evaluate their
own local kernel; they must not introduce recursively nested evaluation of
inherited tensor expressions. Inherited vertices retain separate immutable
descriptions shared by reference.

Gate: the universal parent-child identity and structural invariants are proved;
independent finite full-point comparisons and recipe/precision mutations pass.
Direct parent contraction is an oracle only, never the algorithm's answer.

**9. Implement source-prescribed all-node Hermite recovery.**

Current edit sites: `eth_interpolation/source_hermite.py`, extension Lagrange
interpolation, precision/recovery modules. Keep the bounded rational routine
as an independent reference while adding the general resource-admitted kernel.

For h=ceil(3M/u), nonzero t in S, and i=v2(t), use exactly

```
q_t = h*max(0,u-i)
D_t = L/2^i
p_t = p + 8*h*D_t + 8*M*(a+1).
```

For each active t, the source computes the polynomial F(t+alpha*z) from
M*(2L-1)+1 residue-distinct field-lift evaluations. Their pairwise differences
are units. Interpolate over A_(p_t); then retain the first q_t coefficients.
Do not replace this by q_t scalar samples without a separate justified method.

Implement E_t and the recovery functional in `eq:tensor-hermite-origin`.
Prove interpolation uniqueness, truncated reciprocal integrality,
v2(E_t(0))>=-6*h*D_t, and the evaluation-loss bound. Rational terms can have
even denominators: combine with exact common-denominator arithmetic, prove
integrality and cancel powers of two before final modular reduction.

Gate: for every admissible polynomial, allowable perturbations of supplied
jets modulo 2^p_t do not change the recovered residue modulo 2^p. Independent
fixtures cover degree/multiplicity boundaries, negative nodes and insufficient
guard precision. A larger arbitrary precision is not the source proof.

**10. Compose the recursive function and its correctness induction.**

Implement one depth-first executor using steps 2-9. A source-shaped experimental
entry point may be tested before final qualification, but must retain an
explicit experimental status. Do not enable the existing theorem mode early.

The recursive control flow is:

```
contract(context, node):
    check root-context and entry-description invariants
    if proved_small_size_base_case(context):
        return direct_sum(node)
    if node.edge_count <= context.H_leaf:
        return direct_sum(node)
    plan = checked_source_schedule(context, node.depth, node)
    packing = construct_and_check_packing(node, plan)
    for each active Hermite node t:
        for each required field lift zeta:
            modes = complete_source_modes(node, packing, t, zeta, plan)
            total = 0
            for each certified retained tuple beta:
                term = 1
                for g in range(64):
                    child = construct_checked_child(node, packing, modes, beta, g)
                    term *= contract(context, child)
                total += term
            feed total to the point-interpolation accumulator
        retain the required Taylor data for t
    return checked_source_Hermite_recovery(data, node.precision)
```

This is a specification, not drop-in code. Every helper above has the preceding
proof obligation. In Lean, recurse on the natural edge count and use strict
child shrinkage for termination. Prove precision, degree, graph denotation and
creation-lift invariants simultaneously with correctness.

Gate: the general induction closes. Seek scaled multilevel fixtures under
explicit limits for engineering coverage, but do not claim those fixtures are
source-active. A timeout is INCONCLUSIVE, not a successful recursive test.

**11. Connect exact CNF counting, then implement the arbitrary-density reduction.**

First complete `source_cnf.py`/`source_cnf_check.py` and a source-context analogue
of `tapered_v4/cnf_count.py`. Use distinct-variable clause tensors, bounded-degree
equality trees, and edge subdivision to obtain a bipartite network. Prove unique
extension of each assignment through those gadgets. Handle tautologies, empty
clauses, repeated literals, disconnected components and unused variables.

For this direct Boolean encoding use P0=n+1 and ell=1. Multiply by 2^unused;
the least nonnegative residue then uniquely recovers a count in [0,2^n].
Use s=n+m, and prove the degree/description bounds needed by the contraction
interface. This establishes the fixed-density route once contraction is proved.

Only then implement `subsec:sharp-dense` and `lem:tensor-sparse-query`: the
specific count-preserving sparsification, parity tests, greedy selection,
truncated polynomial encoding and wire-budget argument. Ordinary decision-SAT
sparsification or solving every original clause network does not establish the
same arbitrary-density bound. Track the source's V truncation and precision
requirements through this reduction.

Gate: the complete reduction preserves the count and meets the contraction
interface. Keep the two source conclusions distinct: fixed density has exponent
O_k,D(n/sqrt(log n)); the arbitrary-density statement includes log log n.

**12. Prove cost and qualify the same executable.**

Define the recurrence with every t, interpolation value, retained tuple, and
group child included. Charge exact arithmetic bit lengths, packing searches,
mode construction, entry evaluation, interpolation/recovery, representation
allocation, and any mandatory certificate checking. Include the source's
exp(O(L log s)) packet-entry routine; scalar operation counters are insufficient.

Prove mode multiplicity and tuple-count bounds, the depth-dependent fanout,
precision growth, leaf cost and description growth for the implemented kernels.
Do not substitute a dense enumeration or rational reference algorithm without
proving that its own cost fits the claimed bound.

For polynomial workspace, retain only the current path, current tuple/product,
running sums, necessary interpolation data, and bounded immutable descriptions.
An in-memory transcript of every recursive call can destroy that guarantee.
Keep full-transcript experiments separate; the qualified algorithm must not
retain an exponential call tree or unbounded memoization table.

Finish the executable trust argument: verified extraction/intermediate
semantics, or a clearly specified compiler/runtime trusted base plus proved
checker soundness and source correspondence. If machine-level refinement is
required and unavailable, leave that qualification BLOCKED even if the Lean
algorithm theorem has been proved.

Gate: correctness, termination, reduction, and bit/time/space bounds refer to
the same algorithm and representation. Reproduce the pinned Lean gate, full
Python suites, C++ differentials, independent faults, source-bound evidence and
clean-archive tests. Enable theorem qualification only after the full gate
passes; bounded runtime refusal remains a distinct operational outcome.

**Immediate implementation slice.**

Start with steps 1-4: freeze the streaming labeler semantics, prove candidate
order and whole-run simulation, finish finite-domain packet cardinality, and
create the separate source context with s distinct from M. This completes the
next dependency without changing the already-tested finite recursor's meaning.
Then establish the universal algebra/expansion/child/recovery identities before
integrating them into source-scheduled recursion. Do not schedule a performance
release or promise theorem completion before those mathematical gates close.

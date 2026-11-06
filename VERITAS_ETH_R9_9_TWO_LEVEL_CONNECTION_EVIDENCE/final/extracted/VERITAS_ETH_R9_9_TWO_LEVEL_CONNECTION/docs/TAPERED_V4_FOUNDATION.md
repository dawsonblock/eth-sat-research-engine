# Bounded tapered v4 foundation

`veritas.research.tapered_v4` is an experimental finite implementation of a
depth-configurable recursive control path. It reuses the existing immutable
creation-time tensor recipes, finite packet construction, exact geometric
point modes, and mixed-precision Hermite reference. It does not implement or
prove the manuscript's full schedule or subexponential complexity.
The source reference is OpenAI/math commit
`4eaee87548250b2682affda7d05d947c05554bae`; recording that revision does not
verify the manuscript's proof or this implementation's correspondence to it.
`inspect_finite_schedule` independently reports the exact degree, minimum
number of interpolation points, required extension degree, and per-node guard
precision for supplied scaled parameters. For 16 wires, `a=u=1` and target
precision 17, it reports 49 points, extension degree six, and a required
working precision of 1041 bits; this exceeds the current 1024-bit ring cap.
The numeric report does not certify the theorem schedule or a packing.

```python
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.tapered_v4 import (
    TaperedState, RecursionPolicy, contract_recursive, replay_certificate,
)

cnf = CNF.from_lists(2, [[1, 2]])
f = first_irreducible(5)
network = describe_integer_network(from_cnf(cnf), creation_precision=3,
                                   defining_polynomial=f)
state = TaperedState(network, 0, 3, f, 1, network.edges)
policy = RecursionPolicy(allow_nonshrinking_leaf=True)
out = contract_recursive(state, policy)
if out['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE':
    assert out['result'] == ((3, 0, 0, 0, 0),)
    assert replay_certificate(state, policy, out['certificate'])['valid']
```

The returned value is a residue in the stated extension-jet ring. Recovering
an integer Boolean count requires a count-preserving CNF reduction and enough
root precision; see `eth_arithmetic.boolean_count`. The transcript hash binds
the immutable network descriptions, creation precisions, finite policy, mode
certificates by digest, child results, and final residue. Replay regenerates
the same finite computation with the same implementation. It detects
alterations but is **not** an independent mathematical proof.

## Execution and invariants

- The policy fixes one scaled `(a,u,r)` parameter triple. Each active node
  checks its inherited coefficient ring, creation precision, mode
  certificate, divisibility weights, weighted tuple cutoff, and child
  descriptions. Parent and child degrees are checked against the caller's
  finite cap. The defining polynomial stays fixed across the recursion.
- Each retained tuple records its declared weight and a valuation bound from
  the checked coefficients. Before any child runs, the recursor also checks
  that child wire counts sum to twice the parent wire count. This sum is
  necessary accounting; it does not prove a child identity or uniform shrink.
- The public root must declare its actual edge count. The finite state rejects
  extension polynomials above degree eight before testing irreducibility.
  Internal packing assertions and verifier resource exhaustion return an
  inconclusive status without a partial count.
- Active children must be strictly smaller than their parent. An equal or
  larger child returns `INCONCLUSIVE_NONSHRINKING_CHILD`, unless the caller
  explicitly enables a bounded direct-leaf fallback. That fallback is
  recorded in the transcript and is never a theorem-size claim.
- `require_one_eighth_shrink=True` instead rejects any child that fails the
  strict one-eighth or `6M/r` check. Reaching a depth, work, precision,
  interpolation, tuple, description, or certificate cap returns an
  inconclusive result with no count or partial certificate.
- `mode='theorem'` currently returns
  `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`. A requested hard process
  memory limit or complete bit-work ledger also returns inconclusive: neither
  is implemented by the in-process reference.
- The ordinary path never calls the `4^M` direct point oracle. Setting
  `verify_small_nodes=True` enables a separate bounded direct **node**
  contraction and records its work separately. Exact finite leaves still use
  direct edge enumeration and can require exponential work.

## Current bounds and accounting

The active mode builder defaults to at most six parent wires; a caller can
opt in to at most eight. Direct leaves support up to 16 wires. The supported
scaled packet sizes are two and four, radix is two through four, interpolation
uses the existing degree-31/32-point reference, extension degree is at most
eight for active calls, and precision is at most 1024 bits. The implementation
supports a configured depth up to 64, but a deeper request may exhaust another
budget first; that is not a guarantee of successful recursion at that depth.

The ledger records selected events, observed mode counts by weight,
direct-leaf work, optional node-oracle work, and operand bits for the
recursor's own accumulators. A per-point multiplicity check is recorded as an
instance observation, not assumed to hold uniformly. The initial packet-label
constructor charges cooperative ticks to the shared budget; subsequent packet
verification and source replays are not fully charged. The ledger explicitly
marks itself incomplete: packing verification, mode generation, interpolation,
bit complexity, allocation, and peak RSS are not fully charged. The deadline
is cooperative and may be exceeded while an existing helper is running. The
certificate has a serialized-byte cap, not a hard process-memory guarantee.
Mode lists, interpolation values, and the bounded transcript are materialized;
only retained tuples are streamed. After each finite interpolation the
implementation retains only the jet prefix required at that Hermite node,
although the interpolation itself still materializes the full polynomial.
Consequently this is not yet a polynomial-space theorem implementation.
The `parent_certificate_hash` state field currently holds a digest of the
parent's immutable input state; it is not a proof that the parent result is
correct.

For networks with at most three parent wires, `direct_tuple_contribution`
is a separate finite oracle. It enumerates half-wire assignments and affine
row selections for one retained tuple without evaluating the generated
packet-entry coefficient dynamic program. Its exponential work and explicit
budget make it a correctness reference. The standalone
`certify_point_mode_tuple` replays the mode certificate and reports a
coefficient-derived valuation bound, including for tuples above the cutoff.
The finite Hermite reference accepts coefficient-specific precision
declarations and checks each used reconstruction weight's guard requirement.

An eight-wire forced-assignment CNF completed one tapered step with a
five-dimensional extension and an independent direct-node check. Its largest
child had six wires, not fewer than one eighth of the parent. A separate
two-wire CNF completed two active levels only by explicitly falling back on
nonshrinking finite leaves. These are correctness experiments, not evidence of
uniform shrinkage or a speedup. General 10--16-wire *active tapered* calls
remain unsupported; they may be evaluated only as bounded direct leaves.

## Child wire accounting and the six-edge witness

For each parent wire `e=(u,v)`, the current child builder creates two Boolean
half-wire variables: `Y_e`, assigned to the row endpoint's group, and `X_e`,
assigned to the column endpoint's group. Thus for group `g`,

`M_g = |{e : row_label(u_e)=g}| + |{e : column_label(v_e)=g}|`.

Across all groups, every `Y_e` and `X_e` occurs exactly once, so the sum of
child wire counts is exactly `2M`. The new packet tensors add factor vertices
and incidences on those variables. In this representation they do not add
new Boolean wire variables: `DescribedNetwork.edges` counts variables, and
each variable has one inherited-factor endpoint and one packet-factor
endpoint. The child audit records both wire counts and factor-port counts so
those two quantities are not conflated.

This gives a local conditional bound. If a verified packet assignment has
per-side, per-symbol load at most `3M/r`, then each group obeys
`M_g <= 6M/r`. For `r=64`, this is `3M/32 < M/8`. The implication follows by
adding the row-side and column-side loads; it does not prove that the required
load bound holds for every recursive input or that the theorem's packing
hypotheses are satisfied.

The recorded finite witness has `M=8`, `r=4`, node `-1`, point zero, and
`beta=[]`. Its four child wire counts are `6, 6, 2, 2`, summing to `2M`. The
largest child has ratio `6/8=3/4`; it fails both `M_child < M/8` and
`M_child <= 3M/32`. The finite packing checker reports that the D.3 numeric
preconditions and packing-count bound are false for this tiny instance, so
this is evidence about the finite schedule only, not a counterexample to a
theorem whose hypotheses require a different parameter regime.
In this instance `r=4`, `a=1`, `D=16`, `H=2`, and maximum side degree
`delta=1`: the checked conditions include `M=8 < 2D^2 delta=512`,
`M=8 < L D=32`, `2L=4 > delta=1`, and `D H=32 > 3M=24`. Group 0's six
wires are precisely four row half-wires plus two column half-wires.

`build_finite_child_size_certificate` and
`check_finite_child_size_certificate` reproduce the half-edge partition,
count all child factor ports, and reject tampered counts or any forged
theorem-eligibility flag. They deliberately always report
`theorem_premises_verified=false` and `uniform_shrink_verified=false`: one
finite point and tuple are not a uniform recursive proof.

The finite recursor also replays the expected group, inherited-factor, and
packet-port topology for every generated tuple before evaluating its
children. It derives half-wire memberships from the parent endpoints and
checked packet slots rather than relying only on the sum of child sizes.
The audit distinguishes inherited packet tensors from newly introduced
packet factors by their role in the child graph. These checks establish
topology for the generated finite descriptions; they do not by themselves
verify packet coefficient identities or establish the packing lemma at all
theorem-scale calls. Their internal work and allocation are not fully
metered by the current ledger.

When a direct leaf exhausts its cooperative work budget, the ledger now
records the subcall work reported before failure, separately for algorithm
and oracle leaves. An interrupted run remains inconclusive and its ledger is
not complete bit-operation or memory accounting.

The v4 recursor also charges cooperative work units while it scans and
traverses structural weighted-tuple prefixes, separately for initial
precount, mode-certificate replay, and execution. The callback checks the
shared deadline during those traversals, including before an empty tuple.
It does not meter the separate nominal weighted-tuple dynamic program,
remaining mode and packing verification, arithmetic bit costs, or peak
memory; these are not covered by a complete runtime or space claim. If this
newly observed work exhausts a budget, the result is inconclusive and does
not contain a partial count.

Reproduce the eight-wire witness with:

```sh
PYTHONPATH=src python scripts/audit_v4_child_sizes.py /tmp/child-size-audit.json
```

The remaining theorem work is to prove that the pinned deterministic packing
is applicable at every active call, obtains the needed per-side symbol-load
bound under its explicit hypotheses, preserves the exact tensor identity,
and combines with a bound on the number and cost of all retained children,
interpolation, arithmetic, and leaves.

See [the complete child-shrink theorem plan](CHILD_SHRINK_THEOREM_PLAN.md)
for the conditional proof, deterministic packing derivation, uniform
recursion obligations, implementation stages, and acceptance gates.

The current v4 recursion now uses a sparse occupied-slot packet source and
the point-mode/child path reads occupied slots without expanding packet
padding. The conditional-expectation trace can be independently replayed, and
`audit_d3_child_wire_loads` checks every group at a selected coordinate. These
finite checks do not implement theorem mode or establish the uniform theorem.

The finite point-mode reference supports packet sizes 2, 4 and 8 and radix
through 64, subject to the existing parent-wire, mode, precision, tuple,
interpolation and cooperative work limits. The v4 finite policy also accepts
`a=3` and radix 64. A one-wire run with these parameters completes and agrees
with a direct node oracle, but uses nonshrinking direct leaves. It is neither
a theorem-schedule execution nor evidence of a subexponential bound. The
separate opt-in geometry-mode API can check noncanonical packet assignments;
the v4 recursor still requires its canonical packing source.

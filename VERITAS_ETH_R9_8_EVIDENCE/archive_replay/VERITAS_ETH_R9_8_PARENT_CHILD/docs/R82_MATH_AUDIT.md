# R8.2 finite mathematics audit

## Scope and source lock

This release adds independent finite checks for the contraction machinery. It
does not implement or prove the complete OpenAI algorithm. The pinned source is
the vendored 25 October 2026 manuscript. Its tree SHA-256 is
`f4a10137d8630cb8ff26d031aca38c23a39db4606a4494ff7e43f59b8c671594`; the
SHA-256 of `paper/quantitative-contraction.tex` is
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The code-to-paper references used here are `eq:tensor-cauchy`,
`lem:tensor-integrality`, `subsec:tensor-modes`,
`eq:tensor-mode-expansion`, `eq:tensor-mode-multiplicity`,
`eq:tensor-mode-budget`, `eq:tensor-partition-count`,
`subsec:tensor-children`, `eq:tensor-recursion-identity`,
`lem:tensor-packets`, `eq:tensor-packing-conditions`,
`lem:tapered-hermite`, `eq:tensor-precision-bound`, and
`subsec:tensor-cost`. Historical “Appendix D” names are aliases only.

## Implemented finite checks

`independent_r82/point_mode_oracle.py` builds

\[
C(T)=\prod_{q=-L}^{L-1}(T-q),\qquad
W_{xy}(T)=\frac{C(T)/(T-(y-x))}{C'(0)}
\]

by exact rational polynomial multiplication and long division. It checks
`W(0)=I`, substitutes `T=t+2L Z` over the rationals, then evaluates at one
finite residue point in its separately implemented bounded quotient
`(Z/2^p)[U]/(f)`. Odd denominators are inverted modulo `2^p`; even
denominators are rejected. Its extension arithmetic, irreducibility test,
unit inverse and direct half-edge contraction do not import the production
mode builder, production ring, packing, matching or contraction routine.

It constructs a canonical geometric-mode action from source labels and
compares the complete packet matrix entrywise with the direct rational Cauchy
matrix at each requested point. It also evaluates any supplied local/mode
representation and rejects action mismatches. Algebraically equivalent mode
bases are accepted by action equality. The source edge interpretation and
packet labels remain explicit premises; this does not prove that a packet
assignment meets `lem:tensor-packets` at theorem scale.

`independent_r82/pruning.py` enumerates the bounded exponent box using a
Cartesian product, independent of the production tuple DFS and generating
function counter. For each mode it reads every exact finite row coefficient,
requires the declared weight to be no larger than the minimum observed
2-adic valuation, derives per-mode row support and group-union capacities,
and compares the complete retained sequence. A discarded tuple is accepted
only when its support exceeds a checked pigeonhole capacity or its
coefficientwise valuation lower bound is at least `p`. It does not use
cancellation, does not invoke an unverified division, and does not claim
Hall-based zero pruning. It returns inconclusive on unsupported or excessive
finite domains.

`independent_tuple_coefficient` separately enumerates tiny parent
half-edge assignments and row choices to check each unpruned coefficient.
The selected-point script also compares the complete production child sum
against the independent original-parent half-edge contraction.

## Claim-to-code evidence register

| Mathematical claim | Implementation | Independent check | Evidence boundary |
|---|---|---|---|
| `eq:tensor-cauchy`, `lem:tensor-integrality`: packet kernel and origin identity | `independent_r82/point_mode_oracle.py:cauchy_polynomial`, `shifted_cauchy_polynomial` | Exact `Fraction` long division and `W(0)=I` for `L=1,2,4,8`; production action comparison at tested points | Finite packet sizes and supported integral shifts only |
| `eq:tensor-mode-expansion`: local-plus-geometric action | `point_modes.py:make_point_modes`; independent evaluator in `independent_r82/point_mode_oracle.py:verify_point_mode_action` | Independently rebuilt canonical action and direct rational Cauchy matrix compared entrywise; mutations rejected | Selected nodes, residues, labels, widths and precision caps; no all-parameter proof |
| `eq:tensor-mode-multiplicity`, `eq:tensor-mode-budget`: finite weight/multiplicity restrictions | `point_modes.py`, `structural_tuples.py`, `tapered_v4/recursor.py` | Formula checks in inherited conformance tests; R8.2 valuation and tuple-set audits | Numerical and finite checks do not prove the paper's asymptotic bound |
| `eq:tensor-partition-count`: complete retained tuple sequence | `tuple_stream_check.py`, `independent_r82/pruning.py:audit_finite_pruning` | Production stream compared with a separate bounded Cartesian-product enumeration; injected duplicates, substitutions and omissions rejected | Exact within each checked finite mode list and cap |
| `eq:tensor-recursion-identity`: parent-to-child contraction | `point_children.py`, `child_recipe_check.py` | Tiny unpruned coefficient enumeration plus independent parent half-edge contraction; selected 4/6/8-wire point sum | No universal identity across source-defined depths/parameters is claimed |
| `lem:tensor-packets`, `eq:tensor-packing-conditions`: packet count and port loads | `eth_packing_v26/implicit.py`; actual child load report in `child_recipe_check.py` | Finite packet/replay checks and constructed-load audit | The theorem's very-large threshold regime is not reached; universal packing/shrinkage is unimplemented |
| `lem:tapered-hermite`, `eq:tensor-precision-bound`: tapered recovery precision | `eth_interpolation/source_hermite.py`, `tapered_v4/recursor.py` | Inherited exact interpolation fixtures, source formula tests, and finite recursor replay | R8.2's independent mode oracle does not prove depth-composed precision for manuscript recursion |
| `subsec:tensor-cost`: runtime and space recurrence | `tapered_v4/budget.py` | Observed finite counters and wall/RSS measurements | Ledger explicitly incomplete; no proof-level bit-time or space claim |

## Reproduced finite evidence

The pinned eight-wire forced-assignment call at `t=-1`, `p_t=521`, and
`zeta=(1,0,0,0,0)` has six modes and 64 retained tuples. Both the child sum
and independent direct parent oracle return
`((169600000000, 0, 0, 0, 0),)`. The R8.2 validation script checks selected
4-, 6-, and 8-wire points (3 checked, 0 skipped). Its classification is
`SELECTED_FINITE_CASES_ONLY`, not all-node coverage. The eight-wire direct
oracle is bounded by 8 edges, 5,000,000 work units and 30 seconds; the
independent mode oracle is bounded by 4,096 packet entries, 1,000,000 work
units and 30 seconds. No OS-enforced memory limit is applied.

The eight-wire recursive run returns the same forced count with 12,297
recursive calls, maximum depth 1, 3,074 retained tuples, maximum child size
6 of 8 edges, maximum precision 521 bits, and 2,299,570 *observed* work
units. This finite run does not establish a multilevel shrinking recursion.
The ledger explicitly excludes source-Hermite planning, interpolation bit
operations, some verification and allocation costs, and peak memory. In the
final R8.2 V3-certificate run the writer process reported 120,094,720 bytes
peak RSS and replay reported 270,516,224 bytes; these are process observations, not
enforced caps or a proof of space complexity.

The dense Cauchy script reports scalar counters 579,584 (8 wires),
4,033,536 (10 wires), and 24,813,568 (12 wires) where its bounded
reconstruction completes. These counters cover the script's stated scalar
operations only. They are not runtime, bit-work, or a complete recurrence.

## Adversarial checks and threat model

Focused tests mutate modes by omission, duplicate insertion, wrong row
support, wrong coefficient/sign/shift/point, duplicate row record, and
overstated valuation. Tuple tests include duplicates, substitution,
noncanonical order, incorrect precision boundary and altered valuation.
Overlapping supports and a Hall-deficient synthetic tuple are retained unless
the implemented pigeonhole/valuation argument proves them zero. V3 evidence
tests change source bytes and file sets, alter the policy and manuscript pin,
change the network binding, reorder JSON keys, truncate events, and forge a
mode dependency.

This protects against the tested implementation faults. It does not defend
against a malicious Python runtime, compromised environment, forged upstream
paper, SHA-256 collision, or an attacker who replaces both code and claimed
evidence. V3 hashes are unsigned content bindings, not a signed build or
proof object.

## Assumptions and nonclaims

Checked premises include the finite network's immutable port structure,
creation-time tensor residues, source packet edge partition, finite extension
polynomial irreducibility, actual encoded mode coefficients, tuple support,
and the selected finite interpolation point. Where the independent oracle
cannot establish a premise, execution is unsupported/inconclusive.

Not established: source-universal mode completeness across all nodes and
parameters; universal validity of the packing construction under the paper's
thresholds; `M_child < M/8` for eligible theorem calls; the full
`eq:tensor-recursion-identity` over every source-defined child and precision;
the composed multilevel `lem:tapered-hermite` recovery; arbitrary-density
#SAT reduction; termination and complete bit-time/space bounds. Theorem mode
continues to return `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

Reproduce with the commands listed in `RELEASE_REPORT_R82.md` and check the
machine-readable files under `validation/r82_*.json`.

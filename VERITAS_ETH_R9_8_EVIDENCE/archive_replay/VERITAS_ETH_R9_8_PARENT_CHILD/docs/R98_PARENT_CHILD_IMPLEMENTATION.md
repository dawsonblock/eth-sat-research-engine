# R9.8 bounded parent-to-child implementation

R9.8 implements the parent/child interface, a complete weighted tuple stream,
64 explicit group children, independent child semantics, and bounded scaled
recursion with exact Hermite recovery. It does not qualify source-active
recursion. The 12/14/16-edge boundary algorithm remains a separate finite method.

The R9.7 archive is unchanged, with SHA-256
`b64fc0cbff2f663bb5b3cccfb0e75a98ff19f6eb0977e02a2fce88810191f896`.
It was extracted into a new repository with baseline branch `baseline/r9.7`
and development branch `dev/r9.8-parent-child`. Both the archived and original
R9.7 trees passed 1,051 manifest entries before development. New evidence lives
in the sibling `VERITAS_ETH_R9_8_EVIDENCE` directory. The development tree retains
historical validation files as historical evidence, not as validation of R9.8.

The manuscript remains pinned at `4eaee87548250b2682affda7d05d947c05554bae`.
`source_registry()` verifies all four manuscript digests and ten labeled
statement ranges. The implementation uses `eq:tensor-parameters`,
`eq:tensor-packing-conditions`, `lem:tensor-packets`, `eq:tensor-mode-expansion`,
`eq:tensor-mode-budget`, `subsec:tensor-children`,
`eq:tensor-recursion-identity`, `lem:tapered-hermite`, and
`eq:tensor-hermite-origin`. No manuscript bytes were edited.

## Implemented interfaces and algorithms

`source_parent_child.py` exports frozen `ParentCall`, `PacketLayout`, `ModeSet`,
`ExponentTuple`, `ChildGraph`, `ChildReductionTerm`, `PointEvaluationCertificate`
and `HermiteRecoveryCertificate`. The implementation resides in
`parent_child_r98/`. `from_described` explicitly converts the finite table port
convention; `from_source` preserves `SourceContext` and `SourceNode` constraints.
The source and finite network classes remain distinct.

Every child binds its parent, layout, modes, exact source and used schedules,
depth, node, extension point, beta, group, inherited tensor references, packet
recipes, original creation precisions, and target precision. Its edge map records
Y/X separately, parent edge, packet, slot, original vertex, and original port
position. Canonical serialization verifies its content digest. Hash equality
does not replace semantic verification.

The canonical packer integrates `eth_packing_v26`, the existing paper packing
checker, and a separate occurrence-based audit of actual slots, labels,
orientation, coverage, capacity, padded packet count and both group loads.
Source requests check all three source inequalities before invoking the packer.
The `scaled_singletons` layout is a deliberately experimental fixture with all
vertices in group zero and one real slot per packet. It fails source packing and
shrink conditions; it is never admitted as a source layout.

Modes are built by the existing geometric evaluator. A separate enumerator uses
rational Cauchy polynomials and independent quotient-ring arithmetic, checks the
entire named basis, and checks its full matrix action. Weighted exponents are
enumerated without structural/Hall pruning. An independent generating-function
count plus strict order and membership checks establishes finite coverage.
Valuation checks justify omitting terms of total weight at least the point
precision. This is an executable finite check, not a universal formal proof.

The production constructor builds exactly 64 children, including empty units.
Packet entries remain lazy recipes; no arbitrary exponential child truth table
is serialized. The independent checker reads the original parent occurrences
and packet data, reconstructs expected port incidence and recipe coefficients,
and evaluates entries by independent polynomial coefficient extraction. It never
calls the production child constructor. A second independent materializer permits
checking compact saved point transcripts containing child digests and values.

For every beta, the product of child contractions is compared with a global
parent formal-coefficient oracle. The complete sum is compared with independent
half-edge Cauchy factor elimination. That backend constructs factors on 2M
variables; it does not confuse an original 2^M contraction with a 2^(2M)
deformation calculation. The coefficient oracle is currently limited to four
parent edges and eight formal modes. Unsupported cases return inconclusive.

`source_recursive_engine.py` exposes separate `contract_source` and
`contract_scaled` entry points. The scaled engine calls itself on actual generated
children, in depth-first order, then interpolates the complete residue-distinct
point grid. Rational Hermite recovery checks every monomial through the degree
bound and every coefficient's precision. Independent values only accept or reject
computed values; no oracle result substitutes for failed recursion.

Scaled recursion terminates at an explicit depth. It reports nonshrinking
children. Source leaves use the existing source leaf executor; active source
calls remain refused until eligibility and refinement obligations have evidence.

## Reproduction

From the development checkout:

```sh
PYTHONPATH=src python -m veritas.research.parent_child_r98 scaled examples/r98_one_edge.json --levels 2 --strategy scaled_singletons --output ../VERITAS_ETH_R9_8_EVIDENCE/two_level.json
PYTHONPATH=src python -m veritas.research.parent_child_r98 point examples/r98_cross_group.json --zeta '[1,0,0,0]' --certificate ../VERITAS_ETH_R9_8_EVIDENCE/point.json
PYTHONPATH=src python -m veritas.research.parent_child_r98 verify-point examples/r98_cross_group.json --zeta '[1,0,0,0]' --certificate ../VERITAS_ETH_R9_8_EVIDENCE/point.json
python scripts/validate_r98_parent_child.py --output ../VERITAS_ETH_R9_8_EVIDENCE/r98_parent_child.json
```

The installed CLI is `veritas-r98`. Input files specify integer tensor tables,
ordered ports, sides, edge count, root size, precision and extension degree.
The two-edge point contains 245 weighted tuples at precision 245, including
structurally zero contributions, and 15,680 group contractions. Larger complete
tuple sets are refused rather than silently replaced with a pruned stream.

The signed one-edge two-level fixture has result `(7,0,0,0)` modulo 32. It uses
1,952 point evaluations and 124,929 calls, with 1,952 nonshrinking transitions.
These counts include all 64 group calls; empty groups are actual unit leaves.
The recursion is performed again for each generated child; no result cache
replaces the second level. Creation precisions remain immutable across both levels.

## Formal correspondence and remaining gates

The Lean gate retains 41 modules. `SourceCreationPrecision.lean` now proves
`coordinates_lift_chain` for any list of later precisions all at least the
creation precision, and `coordinates_two_levels` for two such precisions.
`SourceCreationContracts.lean` checks the exact chain theorem type. Their
axiom reports use only standard `propext` and `Quot.sound`. These are statements
about coordinate lists, not a verified Python evaluator or arbitrary recursion.

| Checkpoint | R9.8 scope |
|---|---|
| R9.8a | Frozen contracts, explicit adapters, canonical child round trips, independent topology checks |
| R9.8b | Independently enumerated bounded modes and complete weighted tuples; lazy entry semantics |
| R9.8c | Full beta-by-64 point identity on bounded fixtures; independent per-tuple and parent oracles |
| R9.8d | Two levels of actual generated children in a deliberately nonshrinking scaled fixture |
| R9.8e | Complete finite point grids, exact coefficientwise recovery and installed CLI |
| R9.9 | Open: universal packet/port/coefficient correspondence, enumeration, full recurrence refinement, source-eligible generation and termination |
| R10+ | Open: complete bit-operation and peak-space bounds |

Source qualification is false. In particular, s=12,14,16 has u=0, and the
scaled 64-group tests do not change that. Positive-u symbolic schedules are not
constructed networks. `SOURCE_RECURSION_CONDITIONALLY_VERIFIED` is not emitted.
`COMPLEXITY_NOT_ESTABLISHED` remains explicit. Resource policies bound dimensions,
tuples, calls, work and cooperative deadlines; they are not hard OS memory limits
or complete bit-cost accounting. Saved recovery verification checks values and
the rational functional; it does not certify a claimed recursive execution trace.

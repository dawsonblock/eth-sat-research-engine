# R9.4 source-state and formal-model foundation

This is a partial research release. It adds a bounded source-state admission
API and closes two Lean-model obligations: complete keyed labeling-run
correspondence and the cardinality of the complete radix-bounded padded
packet domain. It does not execute the manuscript's active recursion.

## Source identity and baseline

The working tree was extracted from
`VERITAS_ETH_R9_3_PACKET_MODEL_PARTIAL_FULL_UPGRADED.zip`, SHA-256
`173bb476ccf87e1f0518f5a2c4e5275e8dd570de41a2e5a7fd0a056e993c543d`.
The original archive and checkout were not modified. Its CRC, safe member
paths, duplicate-name and symlink checks passed; all 682 manifest entries
passed before edits. The baseline 30-module Lean gate was freshly run. The
historical 1,237-test baseline was not separately rerun before editing; use
the new release's executed full-suite results instead.

The unchanged manuscript is `paper/quantitative-contraction.tex`, SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
Its actual labels are `app:tensor`, `subsec:tensor-arithmetic`,
`eq:tensor-parameters`, `lem:tensor-packets`, `eq:tensor-packing-conditions`,
`eq:tensor-mode-expansion`, `eq:tensor-recursion-identity`,
`lem:tapered-hermite`, and `subsec:tensor-cost`. Historical D.3/D.16 names
in code are aliases, not an independent source specification.

## Source state: what is implemented

`src/veritas/research/tapered_v4/source_state.py` adds immutable
`SourceContext`, `SourceTensorReference`, `SourceVertex`, and `SourceNode`.

The context fixes s, C, the entry-cost constants A and b, P0, ell, and f.
It checks lambda = ceil(log2(s)), e = 4*lambda, an explicitly supplied monic
binary-coefficient irreducible f of degree e, and P0,ell <= C*s. The leaf
threshold is exactly ceil(s/floor(sqrt(lambda))). M belongs to the node;
it is never substituted for s. All computations use integers.

A node checks its depth and precision, M*8^depth <= C*s, actual incidence
and degree, exact tagged vertex identities, distinct indexed edge
occurrences, and the fixed f/ell for every tensor. Every edge has exactly
one row owner and one column owner. Empty graphs and scalar tensors are
retained. Every tensor has immutable recipe bytes and a creation precision
pc with P0 <= pc <= p. At the root pc=P0. No evaluation or lifting of the
recipe bytes occurs here.

`inspect_source_node` verifies the actual manuscript bytes and returns
structural and numeric findings with count_available=false. It explicitly
leaves entry denotation, uniform entry cost and ancestry unverified.
`check_source_transition` checks unchanged context, depth+1, strictly
increasing precision, 32*Mchild <= 3*Mparent, nonleaf status and an active
numeric preflight. A small nonleaf with u=0 returns an inconclusive error.
A valid necessary-condition report is not a child-contraction certificate.

Admission is bounded by explicit degree, precision, jet length, description
bytes, edge/vertex count, integer size, depth and coarse algebra-work caps.
These are finite engineering caps. In fact, the supported extension-degree
cap prevents representing the asymptotic active regime: no source-active
execution is advertised. The previous `TaperedState` and its limits are
unchanged. The work estimate for admission is not a measured bit-operation
ledger or a hard process-memory limit.

## New kernel-checked mathematics

### Candidate order and ties

`proofs/D3CandidateOrder.lean` defines `productWords` by repeatedly appending
one digit to each existing prefix. It proves equality with `labelWords` for
all natural r,a, and strict lexicographic ordering of that list. For r>0,
`choose_pair_minimum` proves membership and minimal score, and when scores
tie, the chosen word equals or lexicographically precedes the other word.
Thus score equality cannot conceal a changed tie rule.

The scorer in this model is `D3PythonScore.pyCandidateScore`, whose existing
proof relates the index-based transcription to `concreteD3ScoreCandidate`.
No floating-point comparison is involved.

### Keyed state and complete runs

`proofs/D3KeyedRun.lean` models a dictionary extensionally as
(side, vertex_id, coordinate) -> Option Nat. `Related` states pointwise
correspondence to `PackingPartial`. `writeWord` updates only coordinates
within a word, retaining all other keys; this differs intentionally from
an unconditional replacement until the bounded-support invariant is used.

`write_view` proves the update identity under support below a and word
length a. `write_bounded` preserves that invariant. Induction over an
arbitrary finite vertex list proves `run_correspondence` and
`trace_correspondence`. The sorted-root instance relates all final label
coordinates, every trace (vertex, word, score), and the final scaled
class-square score. Empty graphs need no nonempty-vertex assumption.
Candidate lists are nonempty under r>0. Production's stricter r>=2,a>=1
is contained in this model's domain.

These are MODEL_REFINEMENT_PROVED statements between Lean definitions.
`choose` uses Lean's proved first-minimum operation. The connection to
CPython's loop, itertools, dict, integer runtime and actual compiled C++
remains an audited correspondence and finite differential testing, not
verified extraction. EXECUTABLE_REFINEMENT_NOT_PROVED remains explicit.
The older degree/coordinate-order labeler is unchanged and is not silently
identified with the whole-word labeler.

### Complete finite packet domain

`proofs/D3FinitePacketDomain.lean` separately enumerates:

* positions: every directed class c of length a, with both symbols <r,
  and every offset q<H;
* addresses: every canonical pattern (low<=high<r), each packet index
  j < H/2^equalCount(pattern), and each slot k<2^a.

The address list is not defined as an encoding image. Both membership
characterizations and duplicate-freedom are proved. Under 2^a dividing H,
`totalEncode` and `decodeClass` map between these domains and are inverses.
`domain_permutation` proves the encoded positions are a permutation of the
independently enumerated addresses. Consequently:

    length(addresses r a H) = r^(2*a) * H.

There are no assumed domain-completeness or cardinality hypotheses. The
proof includes H=0, a=0 and r=0 where applicable, as well as equal and
unequal orientations and empty padded classes. R9.3's separate
occurrence-rank proof distinguishes parallel edge occurrences. This result
completes the finite *Lean model* domain count; executable packet refinement,
implicit representation cost and universal source-qualified packing remain
separate obligations.

`proofs/D3R94Contracts.lean` spells the acceptance types independently.
The gate audits exact theorem names and allows only propext,
Classical.choice and Quot.sound. No sorry/admit, new axioms, or unsafe proof
substitutes were added. Mutation tests replacing substantive theorems with
True must fail dependent compilation and clear every positive proof flag.

## Evidence and trust boundaries

The 34-module gate and the 887-check differential harness freshly compile
from sources. The latter covers 23 whole-word labeling runs, independent
rational replay, full traces, final coordinates (including unassigned
coordinates), and seven complete bounded packet domains. Executable #eval
is finite testing; universal model proofs are checked separately by Lean.

Evidence is content-bound, not signed or executor-authenticated. The gate
binds its validator, proof manifest, version and manuscript. The new
harness binds source bytes, package inventory, proof files, policy and
relevant tests before/after execution. Existing V3 transcripts preserve
their own documented scope; a labeling proof does not promote them to
recursive theorem evidence. The CI workflow includes the new differential
step; hosted Actions and server-side required checks were not executed or
reconfigured in this release.

See `RELEASE_REPORT_R94.md` and `validation/r94_execution_summary.json`
for actual commands, test counts and outcomes. Historical evidence remains
in the archive, identified by its old filenames; it is not the new source's
qualification record.

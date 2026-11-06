# R9.2–R9.4 proof obligations and dependency graph

This file prevents R9.1 finite results from being promoted into the full
OpenAI result. The pinned source is `paper/quantitative-contraction.tex`,
SHA-256 `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
Use its labels, especially `lem:tensor-packets`,
`eq:tensor-recursion-identity`, `lem:tapered-hermite`, and
`subsec:tensor-cost`.

## Dependency graph

```text
R9.1A sorted formal order
  └─ formal semantics ↔ Python scorer/state/selector (R9.1B; open)
       └─ executable refinement / C++ correspondence (R9.1C; finite tests only)
            └─ global padded-slot ↔ packet-position model (R9.3 proved; executable bridge open)
                 └─ all-mode child contraction + Hermite recovery (R9.3; open)
                      └─ termination + full recurrence (R9.3; open)
                           └─ bit-time / peak-space bound (R9.4; open)
                                └─ outer #k-SAT reduction and theorem (open)
```

## R9.2 — global packet bijection

The existing Lean results `d3MergeSlot`, class-offset arithmetic and local
orientation lemmas are components. Required additions:

* State finite types for directed class padded slots `(class, slot)` and
  constructed packet positions, including empty classes and padding.
* Define total encode/decode functions with one explicit indexing convention.
* Prove both inverse laws, then injectivity, surjectivity, cardinality equality,
  edge-occurrence preservation, and no slot collisions.
* Cover equal and unequal symbols, row/column direction, all coordinates,
  repeated edge indices, zero/full/partial packets and zero padding.
* Prove correspondence to the concrete Python/C++ packet builder.

R9.3 composes the earlier slot model with actual occurrence ranks, numerical
packet/copy division, bit-list inverses, and computed common padding. Its
30-module Lean gate checks `r93_constructed_edge_contract`, both occupied-slot
inverse directions, injectivity, and padding bounds for every common-width
finite class sequence. The required load and padding premises follow from
`D3PaddedConstruction.paddedHeight`, rather than being assumed by this contract.
The model's bijection is proved; source-level executable refinement and a
formal cardinality equality for the complete finite radix-restricted domains
remain open. See `docs/R9_3_PACKET_CORRECTNESS.md` and `RELEASE_REPORT_R93.md` for
exact statements and current evidence. The bounded independent Python checker
also compares the concrete builders and rejects invalid class buckets.

Do not use `d3_any_order_symbol_port_bound` as a substitute for the global
packet bijection. The kernel-checked pattern model and bounded executable
oracle are not the universal source-to-builder refinement proof.

## R9.3 — recursion, contraction, recovery and termination

The recursor must carry the source hypotheses at every node, not infer them
from observed degrees. It must construct every source-defined mode and every
required child, preserve the tensor recipe and creation precision, and prove
the complete weighted parent-to-child identity at each required node. It must
also establish the source degree/size invariants, exact tapered Hermite nodes
and multiplicities, coefficient precision, recovery functional, child-size
decrease and termination. All 64 children per retained tuple and all
interpolation nodes must be included. The Python finite recursive experiments
do not establish these universal statements. Current status:
`RECURSION_NOT_IMPLEMENTED`; theorem mode remains disabled and the existing
fail-closed inconclusive result must remain.

## R9.4 — complexity and outer reduction

Derive cost for the same complete implementation that has been proved correct:
label/candidate work, exact integer bit lengths, packet construction, modes,
tuple branching, all child tensors, interpolation, certificate construction
and checking, recursive fanout/depth, and leaf counting. Prove peak live memory
from the actual depth-first representation, not from operation counters or
observed RSS. Separate arithmetic operation counts, bit operations, memory
bits and empirical process RSS. Incorporate the full source schedule and
preconditions, then prove the count-preserving arbitrary-density reduction,
sparsification and parity-test stages. The active source regime is beyond
ordinary finite packet experiments; do not materialize such inputs as a
surrogate proof. Current status: `COMPLEXITY_NOT_ESTABLISHED` and
`OUTER_REDUCTION_NOT_IMPLEMENTED`.

## R9.1 bridge gaps to resolve next

1. Define a relation between Python's keyed partial assignment and Lean's
   `PackingPartial`, including freshness/unassigned coordinates and tags.
2. The Lean model score identity (`pyCandidateScore_eq`) is now
   kernel-checked, including diagonal terms, unordered edge-index pairs,
   shared endpoints, repeated edges, mismatch short-circuiting and exact
   `D/r^u` arithmetic. The remaining obligation is to relate the actual
   CPython data/state representation to that formal model.
3. Prove `itertools.product(range(r), repeat=a)` order agrees with Lean's
   `labelWords`. R9.3 now proves first-minimum tie behavior for the Lean
   candidate list, but does not prove the Python enumeration bridge.
4. Prove the selected state transition and the complete sorted-order run
   simulation. Bind the formal model to source using a verified extraction,
   defined intermediate representation, or separately justified source
   correspondence.
5. Extend C++ validation/correspondence separately. Finite differential tests
   are evidence, not a C++ machine-code theorem.

Until those bridges exist, report the specific `LEAN_MODEL_*_PROVED` results
and `EXECUTABLE_REFINEMENT_NOT_PROVED` for Python and C++ executables. The
coordinate-at-a-time implicit builder and whole-word streaming builder use
different labeling orders; neither may silently stand in for the other.

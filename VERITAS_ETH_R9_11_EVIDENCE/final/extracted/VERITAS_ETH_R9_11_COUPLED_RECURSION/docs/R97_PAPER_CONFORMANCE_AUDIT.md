# R9.7 mathematical correspondence audit

R9.7 checks two distinct constructions: conventional Boolean-boundary contraction
and finite instances of the manuscript's packet/mode/recovery identities. The
manuscript-active recursive executor remains unavailable. All theorem execution
and complete complexity qualification flags remain false.

## Source and formula contract

The immutable source is OpenAI's October 25, 2026 preprint at commit
`4eaee87548250b2682affda7d05d947c05554bae`. The contraction file has SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The four LaTeX file hashes, ten exact labels, line spans and statement hashes are
computed by `paper_verification/source_registry.py`. Historical D.x names have no
authority over these labels.

Source: [pinned contraction manuscript](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex).

| Source object | Executable verification |
|---|---|
| `eq:tensor-parameters` | `exact_parameters.py`, independent integer thresholds compared with `schedule_preflight` |
| `eq:tensor-packing-conditions`, `lem:tensor-packets` | `packing_checker.py`, actual occurrences, padded packet counts and symbol loads |
| `eq:tensor-mode-expansion`, `eq:tensor-mode-budget` | independent R82 mode-action/pruning oracle plus R81 tuple membership/order/generating-function count |
| `subsec:tensor-children`, `eq:tensor-recursion-identity` | `child_identity.py`, every group value and complete tuple sum checked |
| `lem:tapered-hermite`, `eq:tensor-hermite-origin` | `hermite_checker.py`, rational monomial functional and coefficientwise precision |
| `subsec:tensor-cost` | recorded dependency; no complete implementation-level complexity proof |

The registry checks exact source bytes and locations. Python formulas are reviewed
transcriptions. This is not an automatic semantic translation or a proof that the
preprint is correct.

The independent parameter evaluator uses integer bisection to verify
`(Delta-1)^10 < s^9 <= Delta^10`, integer ceil-log2 and integer square root.
It computes `u_d=floor(lambda/(131072*2^d))`, cumulative even `a_d`, `L=2^a`,
and `packing_class_count=64^(2a)` separately from the interpolation quantity
`interpolation_scale=L/2^v2(t)`. Invalid denominators and unsupported large
integers are rejected. For large symbolic tests it admits only specified powers
of two; it never constructs a graph of that size.

The symbolic case `s=2^131080`, depth zero and degree one passes the necessary
numeric preflight with `u=1`, `a=2`. This supplies no network or child identity.
At `s=16`, `u_0=0`. The new finite grid records both that source schedule and
its experimental `a=2,u=1` parameters. The packing inequalities, root-degree
condition, ancestry size bound, leaf rule and positive-u condition remain separate.

## Complete finite packet identity

For the two-variable formula `(x1 or x2) and (not x1 or x2)`, the new runner uses
four literal-occurrence wires, 64 groups, packet width four, root precision three,
extension degree five, degree bound 28 and four Hermite nodes. All 29 extension
points per node are evaluated: **116/116 points**, **452 tuples**, and **28,928
group contractions**. Both exact reconstruction paths give residue `(2,0,0,0,0)`.
The old four/eight-wire grids remain separate 26/50-point experiments.

The saved certificate is checked against externally supplied parent, parameters
and freshly constructed expected mode data. The checker consumes the submitted
stream; it does not accept a fresh successful run as a substitute for that stream.
Every group, including unit groups, must be present with the right descriptor,
precision and independently calculated value. Missing terms, same-length tuple
substitution, altered coefficients/recipes, mode omissions, changed source or
coverage, and compensating wrong group values are rejected.

The independence boundary is explicit:

* Mode action is recomputed with the R82 rational polynomial oracle.
* Tuple constraints and completeness use the independent generating-function
  count, canonical order/membership checker and bounded unpruned expansion audit.
* Expected child descriptions share the production constructor and its existing
  independent recipe checker. Child entries and contractions use R95's separate
  integer-polynomial arithmetic and factor-elimination oracle.
* The complete sum is compared to an independently evaluated parent half-edge
  action. That parent value can only accept or reject; it cannot replace a child
  sum or supply the reconstruction answer.
* Newton interpolation is evaluated back at every sample. A separate exact
  rational functional checks every monomial through the degree bound and recovers
  each coordinate with its source-prescribed precision.

These are finite checks of a shared mathematical specification. They do not prove
the child generator for arbitrary networks, universal mode completeness, or
creation-lift composition at arbitrary recursive depth. The largest child in the
new grid has four wires, equal to the parent's size. Its finite packing fails the
source packet bound. Therefore this experiment cannot justify termination by the
paper's child-shrinking argument.

## Boundary construction and Lean bridge

`BoundaryGather.lean` proves that the actual little-endian gather address equals
the original table address obtained by restoring fixed bits and reading free
bits. `restricted_eq` proves equality of entries under this construction.
`BoundaryPartition.lean` proves a network-level identity:

`Z(ts) % 2^p = (sum_b Z(restrict(L,b))*Z(restrict(R,b))) % 2^p`.

Its hypotheses require `ts.Perm (L ++ R)`, left ports within the boundary/left
domain, and right ports within the boundary/right domain. The global numbering
concatenates boundary, left-internal and right-internal wires. The proof splits
all Boolean assignments and preserves every factor occurrence. It is a substantive
universal statement about the specified Lean table model, including signed entries.
`BoundaryGatherContract.lean` separately types the entry, recovery and partition
contracts. The live gate checks axiom reports and rejects a replacement `True`
partition theorem.

`validate_r97_bridge.py` generates 16 kernel-checked equalities from actual Python
child tables with asymmetric entries, reversed port orders and noncontiguous free
wire IDs. Changing one generated entry makes Lean reject the fixture. These
concrete checks improve the model/executable bridge. A universal proof that Python's
arbitrary edge reindexing and recursive traversal implement the normalized Lean
model remains missing. No CPython or C++ machine-code verification is claimed.

The independent boundary-tree checker separately verifies incidence partitions,
all boundary masks, every restricted table, every child product and the root sum.
It never invokes the production cut, gather or recursive executor. Admission,
hashing, policy types and the Factor data model are shared primitives.

## Open proof dependencies

1. Verified source-to-model refinement of actual packet, mode and child generation.
2. Universal source-eligible packing and actual load bounds at every active call.
3. Complete source mode/pruning identity and creation-precision preservation at
   all depths, with recursively generated children and source Hermite recovery.
4. Termination for that same executor, including every branch and node shape.
5. Arbitrary-density #k-SAT reduction and complete bit-time/peak-space bounds.

Theorem mode and source-active execution retain their inconclusive safeguards.
The formalization's separate scope is not a certificate for this Python package.

# R9.9 general packet components — partial development milestone

The new `veritas.research.parent_child_r99` path implements bounded general
occupied-packet mode generation, fixed-coefficient verification, complete point
execution, and a strict finite recursive driver. It uses the pinned manuscript's
geometric formula and tapered precision formulas. Source qualification remains
false. `contract_source` is unchanged and still refuses active source execution.

## What changed

`build_packet_modes` handles all real slots, local interactions, tiles, geometric
orders and source/target groups for a supplied independently audited layout.
Modes shared by several rows retain their higher exponents. The builder computes
the complete weighted tuple cardinality separately from execution admission.
A large cardinality can be inspected but is not permission to skip tuples.
`evaluate_packet_point` enumerates every retained weighted tuple or refuses the
whole point before child calls. Algebraically zero source forms and identically
zero coefficient vectors are omitted; the raw padded formal mode domain is not
enumerated. No binary tuple restriction is used.

`verify_packet_modes` recomputes the basis using rational shifted polynomials
and separate extension arithmetic. `verify_packet_term` checks all 64 actual
children with the existing independent port/recipe verifier and compares their
product with independent parent polynomial factor elimination. It verifies a
specified coefficient, not the complete point or a recorded recursive execution.
The independent recipe evaluator now permits up to 128 target modes, using
componentwise truncation above the requested coefficient only for inventories
larger than eight. Nonnegative exponents cannot decrease; this truncation does
not alter the weighted tuple stream. The original small full-polynomial oracle
remains in place.

`contract_packet_recursion` uses an explicit finite depth schedule and audited
packet layouts. Every nonleaf transition checks all 64 actual children against
`64*M_child <= 6*M` before recursive invocation. Only nodes with at most four
edges terminate successfully. Depth, schedule, arithmetic and tuple exhaustion
return no result. Its production values come from generated children and exact
Hermite recovery; independent contraction oracles are confined to verification.
The independent topology checker constructs expected recipes but does not
contract the parent. This is a bounded executable prototype, not a proof of
Python execution or a source-sized implementation.

`make_packet_plan`, `packet_points`, and `recover_packet_grid` support the
existing bounded `1 <= u <= a <= 3` range, including multiple valuations.
They require the complete degree `M(2L-1)` grid at every active node and check
coefficientwise rational Hermite recovery. Submitted sample recovery alone does
not certify those samples; the independent point tests supply that evidence.

## Demonstrated and outstanding acceptance criteria

| Criterion | Evidence scope |
|---|---|
| Multiple occupied slots | One packet with slots 0 and 2 |
| Nonzero exponent-two contribution | A shared mode targets both row factors; beta 0, 1 and 2 independently checked |
| Nonconstant tensors | Row tables `(1,3)` and column tables `(2,5)` |
| Independent coefficient agreement | All 64 children checked for each selected beta; complete crossing point remains unevaluated |
| Two active shrinking levels | **Not established** |
| Multiple-valuation recovery | 90 actual point evaluations at six nodes, valuations 0 and 1, on a separate nonconstant local multi-slot fixture |
| Adversarial inputs | Dropped/duplicated modes, wrong source/target/weight/coefficient/count, altered beta/value/child precision, missing child and incomplete grid rejected |
| Source qualification disabled | Preserved throughout |

The crossing fixture uses `a=u=2`, target precision 5, node 1 and scalar
`zeta=2^40`. It has 106 retained modes. The scalar was chosen to keep this finite
basis within the existing 128-mode packet-recipe limit while retaining a nonzero
quadratic contribution. This is an explicitly scaled fixture. Its enormous full
weighted stream is refused, not replaced by a structural or binary stream.

A separate 22-edge matching exercises one active shrinking level followed by
actual child leaves, all 134 points, and recovery of `31^22` at precision 128.
That fixture has local interactions; it does not establish multi-level general
crossing-mode recursion. The tests disable contraction-oracle entry points during
this production run. The mode and packet recipe checkers still run.

## Remaining work

No source-compliant packer correspondence, complete crossing-mode recovered
parent, two-active-level general fixture, transfer-specific or general-recursion
Lean theorem, universal executable refinement, bit-time proof, or peak-space
proof is delivered here. The source schedule and its 64 groups were not changed.
The finite full-stream bottleneck remains visible rather than bypassed.

Current finite bounds include 1,024 graph edges, layout exponent at most 3,
extension degree at most 12 for mode checks, 128 packet-entry modes, 256 grid
points per node in the recursive driver, and explicit precision, calls, work,
time and evidence caps. A lower independent oracle limit can refuse verification.
Work units are not complete bit costs; time checks are cooperative and there is
no hard memory guarantee. Raising these bounds is not a complexity proof.

Run component evidence from the checkout, using a fresh external path:

```sh
PYTHONPATH=src python3 scripts/validate_r99_packets.py \
  --output ../VERITAS_ETH_R9_9_GENERAL_PACKETS_RUNS/components.json
```

The component validator checks selected higher-order coefficients and complete
local multi-valuation recovery. Its success label does not claim all eight
milestone criteria, source recursion, or full crossing-point evaluation.

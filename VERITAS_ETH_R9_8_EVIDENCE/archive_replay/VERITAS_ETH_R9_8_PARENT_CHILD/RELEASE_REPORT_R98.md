# R9.8 bounded parent-to-child release

Package: `veritas-eth 3.8.2.post98`. Branch: `dev/r9.8-parent-child`.

R9.8 adds independent construction semantics for actual 64-group children,
complete weighted tuple enumeration, lazy packet tensors, and two-level scaled
recursion with coefficientwise exact Hermite recovery. The source-active theorem
executor remains unqualified. This release does not establish the ETH claim,
source-regime termination, bit-time bounds or peak-space bounds.

## Delivered behavior

* Frozen parent, layout, mode, exponent, child, point and recovery records;
  explicit finite/source adapters; content-bound canonical child round trips.
* Source packing preflight before construction, followed by actual occurrence,
  same-slot endpoint, orientation, coverage, packet capacity and group-load checks.
* Independent rational geometric-mode enumeration and Cauchy matrix action checks.
  The new stream includes **all weighted tuples**, including structural zeros.
  Oversized complete streams return inconclusive instead of being truncated.
* A new production child constructor and a separate checker/materializer that
  does not call it. The checker verifies inherited ports and creation metadata,
  local bit order, mode source/target, packet coefficient recipes and all 64 groups.
* Per-tuple coefficient equality and full point equality against independent parent
  calculations; recursion over generated children; complete point-grid interpolation
  and rational Hermite recovery. Oracle values only accept or reject results.
* `veritas-r98` external CLI and two additional Lean coordinate-lift theorems, with
  an exact chain contract and complete axiom reporting.

Detailed interfaces, commands and limits are in
[R98_PARENT_CHILD_IMPLEMENTATION.md](docs/R98_PARENT_CHILD_IMPLEMENTATION.md).

## Fresh results

| Check | Result |
|---|---|
| Full Python 3.12 suite | **1,506 passed, 2 skipped**, 457.19 seconds |
| New R9.8 tests | **52 passed**, included in the full suite |
| Complete cross-group point | **245 weighted tuples × 64 children = 15,680 group contractions**, independent coefficient and full point equality |
| Generated two-level recursion | **124,929 calls; 1,952 point evaluations; depth 2; residue `(7,0,0,0)` modulo 32** |
| Source shrink on that fixture | **FAIL**: 1,952 nonshrinking transitions; this is explicitly scaled |
| Lean gate | **41/41 modules**, no missing axiom records or nonstandard admitted axioms |
| Lift-chain mutation | Replacing the theorem with `True` is rejected by the typed contract |
| Concrete boundary bridge | **16** kernel-checked fixture equalities |
| Existing 12/14/16-edge matrix | **15/15 cases**, including signed, dense, disconnected, satisfiable and unsatisfiable inputs; routing/refusals recorded |
| Additional finite boundary cases | Three signed, shuffled, repeated-tensor, isolated-scalar cases at 12/14/16 edges |
| R94/R95/R96 and C++ validators | All exited 0; the native scorer self-test also passed |
| R97 64-group grid | Write, independent replay and adversarial mutations passed |
| Existing tapered V3 evidence | Write and replay passed |
| Clean wheel, outside checkout | Python **3.10.19**: two-level R9.8, installed CLI write/replay, and finite 16-edge checks passed |
| Linux Docker | Python **3.12.14**, network disabled, 1 GiB container cap: two-level R9.8 and finite 16-edge checks passed |

The two skipped tests require the optional pybind11 extension, which was not
built. The C++ executable was compiled and checked; those skips are not pybind11
qualification. The Docker checks above are specific installed workflows, not a
claim that the full Python suite ran inside Docker or that hosted CI passed.

The initial unchanged R9.7 baseline run had 1,453 passed, two skipped, and one
environment failure: an elan shim had no default toolchain from a temporary
directory. The same test passed with the pinned Lean 4.35.0 binary. The final full
R9.8 run used that explicit binary. The initial failure log is retained.

## Source and evidence binding

R9.7 archive SHA-256:
`b64fc0cbff2f663bb5b3cccfb0e75a98ff19f6eb0977e02a2fce88810191f896`.
The archived and original R9.7 trees passed 1,051 manifest entries, and the final
original-tree check still passes. Neither the original archive nor its source
tree was modified.

Pinned manuscript commit:
`4eaee87548250b2682affda7d05d947c05554bae`. All four manuscript file hashes and
the ten statement hashes are in the fresh report's source registry.

R9.8 package source binding:
`e5205d68b52431d2fc809d7a234f01d015bf857513e7c4178c5f977af95d4517`.
The checkout, Python 3.10 wheel and Linux image report the same binding. The
validation input manifest also binds proof, script and test files. These are
unsigned consistency hashes, not authenticated provenance or universal proofs.

All fresh evidence is outside the source tree, in
`../VERITAS_ETH_R9_8_EVIDENCE/`. The machine summary is `r98_release.json`, with
individual command logs, source manifests, policies, toolchain versions, Lean
axiom records, point certificates and container/wheel results. The separately
delivered evidence ZIP contains those records. Historical `validation/` files in
the source archive remain historical; their old source bindings are not promoted
to R9.8 evidence.

## Qualification boundary

`PASS_FINITE_BOUNDARY_EXACT` and
`PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY` describe the verified bounded paths.
`SOURCE_RECURSION_CONDITIONALLY_VERIFIED` is not emitted. At s=12,14,16 the source
schedule has u=0; scaled a=2,u=1 is not a source-active call.

The new one-tuple oracle supports at most four parent edges and eight formal
modes. Complete tuple, point, precision, description, work, call and depth caps
can refuse other inputs. A refusal has no result. The full 12–16-edge practical
delivery uses the separate ordinary boundary/elimination engine. No 4^16 direct
half-edge enumeration was used or claimed.

The two-level singleton fixture has real inherited and newly created packet
tensors at both levels, but lacks source packing loads and shrinking children.
Its explicit depth policy supplies finite termination. The new Lean lift-chain
theorem concerns coordinate lists under stated precision inequalities; it does
not verify Python packet evaluation, full recursive Hermite composition, or
arbitrary machine executions. The new theorems depend only on `propext` and
`Quot.sound`; the full gate also permits the standard `Classical.choice` axiom.

Remaining R9.9 obligations: universal source-eligible packing and generation,
packet coefficient and mode/tuple correspondence, executable refinement of the
complete recurrence, source shrinking/degree preservation and termination.
Remaining R10+ obligations: full bit-operation and peak-space recurrences.
Both resource-bound statuses remain **COMPLEXITY_NOT_ESTABLISHED**.

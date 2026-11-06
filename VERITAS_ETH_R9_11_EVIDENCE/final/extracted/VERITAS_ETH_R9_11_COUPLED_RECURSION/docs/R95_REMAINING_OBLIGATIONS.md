# Remaining implementation and proof obligations

**The complete theorem implementation is BLOCKED.** No API in this release is a verified ETH refutation. The bounded entry/leaf implementation closes one necessary execution gap, not the active recursive branch.

| Dependency | Current evidence | Required completion |
|---|---|---|
| Canonical labels and global padded packet domains | Lean model results, finite Python/C++ comparisons, independent certificate replay | Explicit trusted source-to-model/extraction bridge; no finite test can supply it |
| Source-state semantics | Immutable ring/context admission, bounded entry interpreter and leaf evaluator | Uniform description/entry cost and source-active representation; source packet/mode provenance |
| Complete mode expansion | Existing bounded R8.2 oracles and tuple-set checks | Universal source mode completeness, divisibility and pruning proof tied to actual code |
| Parent-to-child transformation | Existing finite child identity checks | All source-defined group children from admitted states; ancestry, inherited descriptions, degree and shrinking invariants |
| Hermite composition | Bounded source recovery, independent loss-grid checks, coordinate lift model | Universal functional and coefficientwise precision recovery through every recursive depth |
| Recursion and termination | Explicit active-call refusal; finite experimental recursor retained | Source-active schedule and all-node invariants; termination by certified actual child size |
| Exact #k-SAT theorem | Finite CNF network identities tested | Arbitrary-density count-preserving reduction, sparsification/parity stages and full correctness |
| Time/space theorem | Incomplete scalar ledger and measured resources | Recurrence for the implemented complete algorithm, all branches, bit widths, allocation and peak live space |
| Independent qualification | Local compilers, tests and hashes | Independent reproduction/trusted toolchain provenance; hosted CI required-check enforcement |

Next executable dependency: define one source child-construction interface carrying the packet/mode certificate, immutable entry recipes and parent dependency, then check its **complete** parent-to-child expansion through the independent half-edge oracle on supported finite states. Do not label it universal without the source hypotheses and proofs.

The smallest positive scheduled exponent `a=2` with `r=64`, `D_arr=2^24` and `Delta>=8` gives the necessary condition `M >= 2 D_arr^2 Delta >= 2^52`. It is not a sufficient eligibility test. Materializing that graph is neither practical validation nor a proof strategy. Tiny `a=1` fixtures do not exercise the source-active regime.

The coordinate lemmas added in R9.5 do not resolve any of these remaining universal contraction, termination or complexity obligations. Source theorem mode must continue returning `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

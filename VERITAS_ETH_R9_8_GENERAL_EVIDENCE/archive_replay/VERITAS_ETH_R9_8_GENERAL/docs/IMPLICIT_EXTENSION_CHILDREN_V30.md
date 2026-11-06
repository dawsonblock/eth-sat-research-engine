# v3.0 Finite implicit extension-ring child tensors

## Scope and claim

This is a **bounded exact reference**, not the specialized D.4.4 geometric-tile/weighted-mode child recursion. It neither proves nor demonstrates the manuscript's subexponential complexity or the `M_child < M/8` theorem. A valid small certificate can have manuscript D.3 *numerical preconditions unsatisfied*. All outputs explicitly identify that status.

## Construction

Given a bipartite Boolean tensor network with `M <= 6` edges, `construct_d3_packing` supplies row/column endpoint labels and padding/aligned packets. Original wire `e` becomes two independent Boolean half-bits `Y_e` and `X_e`. At nonzero interpolation node `t` and `alpha=2L`, the polynomial kernel is evaluated as an exact truncated jet in

`R = ((Z/2^p Z)[U]/f(U))[V]/(V^q)`.

For every real row slot `x`, define `z_x = sum_(y real in packet) W_xy(t+alpha V) X_y` and `H_x = z_x` when `Y_x=1`, otherwise `H_x=1-z_x`. Multiply the original row tensors on `Y`, column tensors on `X`, and all `H_x` factors. Every tensor entry is computed *lazily* from its immutable input and coordinates; it is not materialized as a full dense table.

Assign the original row and column factors to their verified coordinate-`v_2(t)` D.3 groups. A Cauchy row factor belongs to the group of its row endpoint. The set `B` of half-bit variables appearing in more than one group is the global boundary. Each group `g` has local factors `F_g` and internal half-bits `I_g`. Construct its implicit child tensor:

`C_g(b) = sum_(i in {0,1}^I_g) product_(f in F_g) f(b,i)`.

The complete contraction is **exactly**

`Z(t+alpha V) = sum_(b in {0,1}^B) product_g C_g(b)`.

The implementation only evaluates each child on the boundary assignments required, caches them, and enforces a shared assignment/time cap. This identity is a conventional separator factorization. Cross-group variables are conditioned on rather than replaced by the paper's geometric tile modes. It can perform `2^|B|` boundary work plus exponential child work.

## Independent checks

1. Recompute all D.3 class/slot/conditional-expectation invariants.
2. Require exact correspondence between the packet certificate's graph and the input network's factor endpoints.
3. Recompute the complete Taylor jet with a separate direct `4^M` half-edge enumerator, without using the group/child decomposition.
4. At `T=0`, independently evaluate the undeformed network, verify `W(0)=I`, and compare its constant coefficient against `brute_contract` modulo `2^p`.
5. Replay every child boundary/ownership descriptor and the reported result; reject tampered certificates or unsupported claims.
6. Reject resource exhaustion as inconclusive; do not return a partial result.

The `veritas-eth30` CLI and `/v1/research/eth/implicit-children` routes are research-only. Results cannot be promoted to a proof of D.4.4, an improved SAT runtime, or the paper's polynomial-space theorem.

## Next steps

- Replace generic cross-boundary conditioning with the manuscript's correct geometric-tile, valuation-weighted expansion in the extension ring.
- Derive **actual** mode-selected packet child descriptions; check them against this exact reference at every Taylor node.
- Prove independently that eligible child networks shrink to the manuscript's size/degree bounds.
- Integrate tapered Hermite and all precision transitions into the recursion.
- Audit exact arithmetic bit costs and retained-mode counts before making any asymptotic claim.

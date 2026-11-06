# v2.6: finite Appendix D.3 construction, independent certificate checking

## Mathematical source and versioning

Target is Lemma D.3 in the October 2026 manuscript *The Exponential Time Hypothesis is False*. A public readable text includes the proof under "Parameters and collision packing". v2.6/v2.7 erroneously asserted `u_d = ceil(epsilon * lambda / 2**d)`; the published source currently states `floor`. v2.8 restores floor; source remains unpinned to an immutable commit. `eligible` in the parameter service is **only a D.6 numerical predicate**, and is false if `M` and `delta` are not provided; it is not certification of the full theorem.

## Precisely implemented mathematical construction

1. Row-side and column-side vertices are disjoint, even if they share numeric IDs. Assign symbols independently in `[r]^a`.
2. For each *directed* pair-label `gamma=(row_symbol_vector,column_symbol_vector)`, compute the count `X_gamma` of original edges bearing it.
3. Fix every symbol coordinate by exact conditional expectation, minimizing `E sum_gamma X_gamma^2`; the centered potential differs by the constant `M^2/D` with `D=r**(2*a)`. For two edges, the equality probability is a product of at most two independent equality events per coordinate. Multiplication by `D` yields exact integer scores without floating-point error.
4. Let `H` be the maximum directed-class population rounded up to a multiple of `L=2**a`. Every directed class receives *exactly H total positions*, including empty classes.
5. For every unordered symbol-pair vector, packet positions enumerate all `2**a` slot-bit patterns. Unequal pair coordinates select orientation; equal pair coordinates select independent copies. Exactly `D*H/L` packets result.
6. Check all actual wires appear exactly once. Check slot-to-endpoint alignment, the entire directed-class padding census, maximum symbol-port load, packet bound, final centered potential and the full monotone conditional-expectation assignment transcript.

The numeric D.6 conditions checked are:

- `M >= 2 * D**2 * delta`
- `M >= L * D`
- `2 * L <= delta`

Here `delta` is checked against the **observed maximum degree on either side**. Passing these and the independent finite verification establishes that this specific finite layout satisfies the D.3 packet/count/load conditions. It does not certify that the input network satisfies every other hypothesis of the broader ETH theorem.

## Proof-related quantities

`E[sum_gamma X_gamma**2] * D` is an exact integer, as is the score of every conditional assignment. The checker independently recomputes the score and rejects a certificate whose score increases on any assignment. The centered potential is

`Phi = sum_gamma X_gamma**2 - M**2 / D`.

The manuscript upper-bounds the initial expectation by `2*M*delta`. In the finite execution, `D*Phi <= 2*M*delta*D` is verified independently. Packet and port bounds are separately checked; no appeal to the lemma's asymptotic scope is needed for these actual numeric facts.

## Non-goals and restrictions

- **No** D.4.4 weighted cross-group mode enumeration, specialized recursive child tensor construction, subexponential runtime bound, general polynomial-space claim, or end-to-end ETH solver.
- Finite Python implementation is deliberately bounded by a work estimator, at most 4096 directed label classes, 10000 packets, and independent checker limits. Larger inputs return an explicit resource error.
- The v2.5 endpoint-load heuristic remains intact for backward compatibility, but is **not** used as a substitute for this D.3 construction.
- Small scaled examples may satisfy the packet identities but not D.6, and must be reported as such.
- Certificates are not cryptographic signatures and do not establish that a particular manuscript proof is universally valid; they are transparent, replayable finite mathematical evidence.

## Next milestone

D.4.4 proof-aligned valuation-weighted cross-group modes. Inputs to that component should be *verified* D.3 packets; no simulated or heuristic packings may be promoted to theorem-level assumptions.

**Applicability nuance:** The released working example uses `r=2,a=1` to make exact validation practical, not the manuscript’s global `r=64` asymptotic parameter schedule. The certificate explicitly reports `manuscript_fixed_radix`. A passing `d6_numeric_preconditions_satisfied` checks only the three *numeric* inequalities, not full manuscript eligibility.

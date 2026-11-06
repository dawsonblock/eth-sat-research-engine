# R8.2 finite mode and pruning contract

## Contracted finite domain

For a finite mode list `j=0..s-1`, a precision `p`, per-mode row support
`S_j`, and group key `g(j)=(packet,target_group)`, the checker audits

\[
E=\{\beta\in\mathbb N^s:\;0\le\beta_j\le |S_j|,\;
\sum_{j:g(j)=g}\beta_j\le |\cup_{j:g(j)=g}S_j|,\;
\sum_j w_j\beta_j<p\}.
\]

This is the bounded support domain used by the finite child expansion. It is
not asserted to equal the paper's required mode domain for all theorem
parameters. The independent checker reads coefficient residues from each
mode and verifies `w_j <= min_r v_2(a_{j,r})` in the configured quotient.
For each discarded precision term it checks

\[
\sum_j\beta_j\min_r v_2(a_{j,r})\ge p.
\]

This proves the product is zero modulo `2^p` coefficientwise; sums of such
terms remain zero. The zero-residue valuation is defined as `p`, which means
only that the represented coefficient vanishes in this quotient. Odd-unit
arithmetic is valid in the ring. An even denominator is never treated as an
invertible modular element.

## Independent paths

`independent_r82/point_mode_oracle.py` uses exact rational polynomial
division and a separate finite extension implementation to reconstruct the
whole packet matrix and compare its action with the emitted local-plus-mode
representation. It does not call production point-mode generation or
checking. The checker accepts an equivalent basis when its action agrees.

`independent_r82/pruning.py` uses a bounded Cartesian product, not the
production DFS or R8.1 generating-function DP. It derives supports and group
capacities from encoded row records, checks every tuple in the finite box,
and compares the strict canonical emitted sequence with its own retained
list. The mode-action verifier must pass first; a standalone pruning result
does not certify that modes were generated from the source expansion.

For tiny parents, `independent_tuple_coefficient` computes the unpruned
coefficient by exhaustive original half-edge assignments and explicit row
choices. On those fixtures, the test compares the complete unpruned sum, the
valuation-pruned sum, the production child sum, and an independently
contracted parent value modulo `2^p`.

## Fault handling

Malformed mode support, wrong coefficients, duplicate modes/rows,
underestimated declared valuations, invalid precision, out-of-order or
duplicate tuples, a same-length substituted tuple, failed equality, and
resource exhaustion produce an invalid/inconclusive result with no count.
If a weighted discard lacks an independently checked valuation premise, it
is `INCONCLUSIVE_UNPROVED_PRUNING`, never assumed zero. Hall deficiencies are
not removed by this checker; a synthetic Hall-deficient tuple is deliberately
retained unless another checked rule proves it zero.

The independent Cartesian-product cap is at most 1,000,000 candidates. This
is a finite audit bound, not a hard memory guarantee. The point oracle caps
packet entries, precision, extension degree, edge count, work and cooperative
time. A cooperative timeout is not an OS-level CPU or memory isolation
boundary.

## Established and assumed

Established on the checked finite fixtures: exact rational Cauchy construction
and `W(0)=I`; pointwise packet-action equality; finite tuple-set equality;
the implemented support pigeonhole implication; the implemented
coefficientwise valuation implication; and the selected tiny parent/child
sum equalities.

Assumed or outside this checker: packet-label correctness as a consequence
of the general source packing lemma; completeness of all source-required
modes for every depth/node/extension; source-wide validity of every pruning
weight; Hall/matching completeness; universal child-size shrinking; and the
paper's multilevel recursion and complexity proofs. These distinctions are
why this contract only grants finite statuses.

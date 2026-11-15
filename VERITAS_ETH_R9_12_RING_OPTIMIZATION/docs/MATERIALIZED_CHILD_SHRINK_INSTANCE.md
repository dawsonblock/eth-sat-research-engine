# A materialized instance of the child-size bound

`scripts/audit_materialized_child_shrink.py` builds an explicit random
bipartite graph of maximum degree `Delta` at the smallest edge count the
packing lemma permits, draws vertex labels in `[r]^a`, and checks by direct
integer counting every hypothesis and the conclusion of the Lean theorem
`ModeCount.child_edges_of_packing` (`lem:tensor-packets`, item 3).

It complements two things already here. `symbolic_regular.py` gives a
closed-form witness for a perfectly regular family, including at theorem
scale (`scripts/audit_symbolic_theorem_root.py`), without materializing a
graph. The Lean theorem proves existence for every graph. This script is the
missing middle: an unstructured graph, actually stored, counted edge by edge.

## What it checks

With `D = r^(2a)` and `L = 2^a`:

- hypotheses: distinct edges, row and column degree at most `Delta`,
  `2*D^2*Delta <= M`, `L*D <= M`;
- the potential bound `sum_gamma (X_gamma - M/D)^2 <= 2*M*Delta` for the drawn
  labels (cleared of denominators; another draw is taken if it fails);
- padded slots `H_pad*D <= 3M`;
- for every coordinate and symbol, row-side plus column-side edge ends times
  `r` at most `6M`, and at most `M/8` when `r >= 48`.

Labels are random and then verified. The deterministic
conditional-expectation constructor is not replayed at this size.

## Recorded runs (seed 0, NumPy 2.5.3)

| `r` | `a` | `Delta` | minimum `M` | edges `M` | largest child | `M/8` | child / `M` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 48 | 1 | 1 | 10,616,832 | 10,616,896 | 444,189 | 1,327,112 | 4.18% |
| 48 | 1 | 2 | 21,233,664 | 21,233,792 | 888,378 | 2,654,224 | 4.18% |
| 64 | 1 | 1 | 33,554,432 | 33,554,496 | 1,050,301 | 4,194,312 | 3.13% |
| 64 | 1 | 2 | 67,108,864 | 67,108,990 | 2,100,602 | 8,388,623 | 3.13% |

All checks pass in each run. The largest child is close to `2M/r`, which is
what independent uniform labels give; the proved bound `6M/r` is three times
looser. `r = 48` is the smallest radix for which `6M/r <= M/8`.

Reproduce one row with

    python scripts/audit_materialized_child_shrink.py --radix 48 --degree 1

The 64-radix degree-2 row needs about 3 GB of memory.

## What it does not show

- It is off the manuscript's schedule. There `r = 64` and `a = a_d >= 2` at
  any call with a label coordinate, so `M >= 2^49 * Delta`, and `a_d = 0`
  until `lambda >= 131072`, that is `s` about `2^131071`
  (`ModeCount.aSched_eq_zero`). No materialized graph reaches that.
- The graph is synthetic. It does not come from a CNF reduction, and no
  tensor network, mode, child network or contraction is built.
- A child with at most `M/8` edge ends is a counting statement about labels.
  It says nothing about the cost of the recursion, and is not evidence for
  any running-time bound.

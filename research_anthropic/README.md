# Anthropic crossing-reduction reference

This isolated experimental package builds on the supplied
`UniversalSAT_Anthropic_EightSquare_Kernel_A0.zip` (SHA-256
`69eeca3fc8b2f26bd6910019766ed37d67931d2a4f3b8f30e8d408208e1bf052`).
`eight_square.py` is the supplied kernel. It is not UniversalSAT v2, which was
not included in the attachments. This package is part of the current ETH-SAT
0.3.0 workspace; it does not modify the supplied v0.31 or v0.30 archives.

The research reference is Anthropic's [paper at commit 16a5ce4](https://github.com/anthropics/formal-math/blob/16a5ce41304fcdaea4e0be7c132e1c361dc26da5/eth/paper.pdf),
PDF SHA-256 `7af518b09342c967ea371c74b8989806684c5d02aabe5763ca08554aff5025a0`.

## Implemented

* `encode_cnf` builds occurrence variables, per-clause truth conditions, and
  chains of equality constraints, including repeated literals and variables
  that do not occur. `count_occurrences` exhaustively contracts this network.
* `CrossingFactor` implements the two Lemma 2(b) index constructions. It
  exposes the two factors lazily for any index. The compressed path stores a
  bitmask for the chosen C blocks followed by three- or six-bit per-block
  indices; the alternative indexes the entire left boundary. Both count
  exactly the index bits in the paper's `min` bound. This construction is not
  a general low-rank compression of the equality matrix.
* `rectangle_grid` contracts the single rectangle in a 2x2 clique. For each
  coefficient, it chooses one orientation globally, evaluates the two merged
  node sums lazily, sums over the interface and divides exactly by `2^t`.
  `direct_grid` contracts the same clique independently over its six edges.
  The four tables use neighboring vertex order `0,1,2,3`, excluding the
  vertex itself; each neighbor contributes `width` little-endian bits.
* `network_clique.py` adds factorized networks, strict good-group search,
  lazy group tables with padding, general square-grid rectangle expansion,
  global row/column selection per mode, and a bounded configurable recursive
  Network/Clique-shaped evaluator. `cnf_to_network` and `count_cnf` connect
  occurrence-chain CNF encoding to this evaluator. Strict grouping checks
  Lemma 1's inequalities; explicitly requesting `grouping="relaxed"` uses a
  tiny experimental grouping that need not satisfy those inequalities.
  The input network must supply pair functions and factor functions that
  satisfy the factorization identity; this is a caller contract, not checked
  for arbitrary supplied functions.

Example, run from the repository root:

```python
from dataclasses import asdict
from research_anthropic.grid import direct_grid, rectangle_grid

tables = tuple((1,) * 8 for _ in range(4))
original, original_work = direct_grid(1, tables)
result = rectangle_grid(1, tables)
print(original, result.value, result.modes)
print(asdict(original_work), asdict(result.ledger))
```

This instance has original value 64, transformed mode values 64 and 64,
and reconstruction `128 / 2 = 64`. It performs 64 direct edge assignments
versus 4,096 transformed local settings. These are different work units, so
they are not a complete operation count. The ledger also counts selected
outer additions, multiplications, table and factor calls, comparisons, and
the final division. It does **not** count factor-reader internals, loop and
indexing costs, integer bit complexity, storage, or interpreter overhead.
Thus it cannot establish an overall arithmetic or memory bound. Caps are
explicit bounds on enumerated settings, not general time or memory limits.

Run `python -m pytest -q tests/test_anthropic_rectangle.py` for exact
differential and negative tests. The compressed factor test covers widths
5–7 including partially padded blocks; the full transformed grid tests width
1 only, with row and column orientations. Small widths choose the direct
`2*width`-bit factor where that is cheaper; compressed factors are tested
separately, not in an end-to-end compressed recursion.

The additional suite `python -m pytest -q tests/test_anthropic_network_clique.py`
checks randomized CNF and signed clique counts, both directions, all nine
rectangles on selected 3x3-grid settings, the actual compressed-factor path
through a lazy network-to-clique conversion, and generic dense networks with
10 and 15 edges. These latter networks do not use the rectangle deformation.
One recursion level is differentially checked; a two-level schedule is only
checked to reach depth two and stop under the work guard. No two-level result
is claimed.

For example, the following is an opt-in finite CNF experiment:

```python
from eth_sat.model import CNF
from research_anthropic.network_clique import Work, count_cnf

formula = CNF.from_signed_clauses(2, [[1], [-1, 2], [2], [-2, 1]])
work = Work(limit=5_000_000)
count = count_cnf(formula, clusters=4, clique_nodes=4, levels=(2,),
                  grouping="relaxed", work=work)
print(count, work)
```

`Work` charges selected control iterations, table/factor queries and outer
integer additions and multiplications. It does not count all operations within
factor readers, index packing, comparisons, division, integer bit complexity,
or memory. It is a guard on the operations explicitly charged by this code,
not a time or memory bound. Lazy networks and cliques are bound to the `Work`
object used to create them, so nested readers share the same budget. The lazy
tables recompute values on each query.

## Not yet implemented

This is **not** a faithful implementation of the complete paper algorithm.
The finite schedule is supplied by the caller, the paper's huge quantitative
schedule and parameter choices are not implemented, and generic table
evaluation and recursion do not establish the claimed complexity bounds. It
does not implement count-preserving sparsification, the specialized sharper
Appendix B crossing pieces, or a backend integrated into UniversalSAT. It also
does not implement OpenAI's Appendix D
2-adic deformation, modular pruning, or interpolation. No modular mode
survival count, general child-wire reduction, full operation comparison,
subexponential runtime, polynomial-space bound, or universal SAT claim has
been established. Further work includes validating completed multi-level
instances, complete arithmetic and memory accounting, the paper's actual
schedule and sharper crossing construction, and count-preserving
sparsification.

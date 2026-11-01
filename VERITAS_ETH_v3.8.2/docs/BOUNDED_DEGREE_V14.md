# v1.4 — Parsimonious bounded-degree CNF tensorization

## Motivation

The earlier `from_cnf` routine uses a single degree-d equality tensor per
Boolean variable and allocates a dense table of size `2**d`. A variable with
hundreds of occurrences becomes impossible to encode even when all clauses
are short. That is a genuine limitation of the baseline encoding, not an
inherent complexity barrier to representing a Boolean formula as a tensor
network.

## Exact construction

For each literal occurrence, create one wire joining its clause tensor to the
variable gadget. If a variable occurs `d` times:

- `d = 0`: include one scalar factor `(2,)` to count its two choices.
- `d = 1`: unary COPY factor with table `(1,1)`.
- `d = 2`: binary equality factor `(1,0,0,1)`.
- `d = 3`: ternary equality (COPY3) factor, with exactly two nonzero entries.
- `d >= 4`: use `d-2` COPY3 factors joined in a *chain* by `d-3` new wires;
  two occurrence wires attach to each end, and one to every interior node.

Each COPY3 tensor evaluates to 1 exactly when its three incident bits agree.
For every original assignment to `n` source variables, each original clause
wire is forced to match its source variable and every auxiliary wire is
uniquely forced to match it as well. Therefore the product of all variable
factors is 1 for exactly one extension of each original assignment, and 0 for
all other half-wire assignments. Clause factors test the original clauses;
`#SAT(F) = contraction(N(F))` exactly. The argument also covers repeated
literals, tautologies, empty clauses and unused variables.

Let `L` be the total number of original literal occurrences and `d_v` the
occurrence count of original variable `v`. The new network has

    wires = L + sum_v max(d_v - 3, 0)

and a maximum equality-gadget factor degree of 3. Clause factor degree is
bounded separately by `max_clause_width`, 8 by default. This conversion
requires O(L+n+m) factors/wires, subject to constant clause width.
It does not change general counting complexity, since network contraction
may still have exponential induced width.

## API example

    POST /v1/research/bounded-degree-tensor
    {
      "n": 3,
      "clauses": [[1,2],[-2,3]],
      "contract": true,
      "max_table_entries": 65536,
      "max_work_assignments": 2000000,
      "timeout_s": 15
    }

The response identifies the original formula SHA-256, gadget statistics,
selected wire-elimination order, the exact integer count, and the audit record
hash. On requests with <=10 original variables and bounded clauses it
independently checks the final count using the Boolean exhaustive oracle.
A `modulus_bits` request returns only the residue modulo `2**p`, **not** an
exact count. A resource limit returns HTTP 422 and never returns a partial
count. The HTTP process is not an OS-level untrusted-input sandbox.

CLI:

    veritas-cli cnf examples/example.cnf --bounded-degree
    veritas-cli cnf examples/example.cnf --gadget-contract --timeout 15

## Evidence and limitations

Validation compares against an independent Boolean exhaustive oracle on
small cases, including 800 reproducible seeded examples, plus isolated and
high-occurrence adversarial cases. This is robust empirical testing but not a
Lean kernel proof of the general construction. The chain's parsimony follows
from the one-extension-per-assignment argument above.

This is neither the manuscript's sparse parity encoding / sparsification nor
its special D.4.4 collision schedule and mode contraction. It is useful for
representing bounded-clause Boolean formulas as bounded-degree tensors; no
subexponential runtime or practical performance breakthrough follows.

Upstream general tensor theorem (not implemented here):
https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-reduction.tex

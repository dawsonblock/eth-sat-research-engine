# R9.1 complexity notes

These are analyses of the implementation in this repository. They are not
claims about the manuscript's subexponential bound, and no asymptotic
statement here has been formalised in Lean.

## Direct scorer

`_candidate_score` visits every unordered edge pair once and, inside it, scans
`a` coordinates and two sides. Let `M` be the number of indexed edges and `V`
the number of distinct vertices (rows plus columns).

* Per candidate: `O(M^2 * a)` pair-comparison work, with early exit on a
  mismatch.
* Per vertex step: `r^a` candidates, so `O(r^a * M^2 * a)`.
* Whole construction: `V` steps plus one initial pass, i.e.

  `O((V * r^a + 1) * M^2 * a)`.

This matches `estimated_streaming_work`, which charges one unit per pair visit
plus `1 + 2a` per pair. The estimate is an upper bound: early exits reduce the
real count.

## C++ batch path

For one vertex step the pairs split into those incident to the current vertex
and the rest. Only the incident pairs depend on the candidate label. If the
current vertex has degree `d_v` among `M` edge occurrences, its incident-pair
count is at most `d_v*(M-d_v) + d_v*(d_v-1)/2`, hence it can still be
`Theta(M^2)` for a high-degree vertex. Therefore:

* candidate-independent pairs: computed once per step, `O(M^2 * a)` total;
* incident pairs: `O(d_v*M)` in the worst case, `O(d_v*M*a)` per candidate;
* per step: `O(M^2*a + r^a*d_v*M*a)` with early-exit reductions on a given
  input, and worst-case `O(r^a*M^2*a)`.

This is the optimization that `validation/r91_benchmarks.json` measures. It
can reduce repeated work when many edge pairs are candidate-independent; it
does not establish a better worst-case asymptotic bound. It is exactly
equivalent to the reference because the term for a non-incident pair does not
mention the candidate label.

## Space

* The direct scorer keeps no pair table: `O(M + V * a)` for the inputs.
* The batch path keeps at most `r^a` score strings plus the incident and
  independent pair index lists; pair-list storage is capped at one million
  unordered pairs and output at 64 MiB.
* The native backend also caps `r^a <= 100000`, side vertices at 10000,
  edge occurrences at 100000, and conservative per-build work at 100 million
  versioned units. These are implementation guards, not complexity proofs.

## What is not claimed

* No subexponential bound.
* No bit-complexity bound: the analysis counts operations on arbitrary
  precision integers, not machine words.
* The manuscript's active regime (`M >= 2^52` for the smallest scheduled
  exponent) is not exercised by any test here; `docs/R9_SOURCE_AUDIT.md`
  records why.

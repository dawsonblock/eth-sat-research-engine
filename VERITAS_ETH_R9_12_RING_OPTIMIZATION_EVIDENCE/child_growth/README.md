# Top-level recursive child-request census (stopped early)

Produced by `scripts/experiment_r912_child_growth.py` with the default
`finite_layout(a=u=1)`. The sweep was stopped by request; only the completed
instances are kept (circulant offsets 5 and 7 up to 80 vertices per side,
random simple cubic bipartite graphs up to 48 per side). `sweep.log` is the
console output.

Per instance: wire elimination width, interpolation points, the exact
affine-row support size at sampled points (factorized count, never
expanded), children per tuple, and per-child mode dependency sets measured
by single-mode flips with random-tuple consistency checks.

Findings at these sizes:

- Support per point is `2^K` for `K` modes; every mode weight is 1 and the
  maximal total weight is far below the creation precision, so the weighted
  cutoff removes nothing.
- Requested child computations in one top call grow about one bit per wire
  on random graphs (log2 ~77 at 66 wires, ~154 at 144 wires).
- Each nonconstant child depends on 4 to 6 modes. If those sets are exact,
  the beta sum is a mode-variable contraction whose min-fill width equals the
  wire width on circulants and is two to three times the wire width on
  random graphs.

Dependency sets are empirical. None of this is a source-qualified call or
evidence for or against the source theorem's parameter regime.

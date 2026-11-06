# v3.8.1 engineering correction candidate

Based on the user-supplied v3.8.0 source ZIP (SHA-256
`2d07ab851a8af4fc13d3d674bd60407de80fd38dbbfc06a8d4745ecca16f7f72`).

The six reviewed issues are addressed: shared cooperative budgets and phase
ledger, resource-inconclusive verification, factor-content cache keys,
optimization-safe manifest checks, consistent v3.8 budget ranges, and a
complete test extra with a Python 3.10/3.12 CI matrix. v3.8.1 emits a new
certificate schema; old v3.8 certificates fail closed. The v3.7 archive's
certificate replay is preserved and covered by a fixture.

An independent scalar Cauchy testbed covers even widths 8 through 16 with
explicit guards. It does not implement the manuscript's geometric tile modes,
interpolation or recursive child construction. The bounded direct half-edge
oracle is blocked at 16 wires by design. Recorded finite outputs, seeds and
table hashes are in `validation/v381_dense_cauchy.json`.

The cooperative ledger is neither a hard process limit nor complete bit/memory
accounting. No subexponential runtime, `M/8` theorem, ETH result, security
qualification, hosted-CI result, or production readiness is claimed. See
`docs/CORRECTIONS_V381.md` for the source-pinned obligations and limitations.

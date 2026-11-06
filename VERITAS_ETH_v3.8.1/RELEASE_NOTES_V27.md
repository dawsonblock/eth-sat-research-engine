# VERITAS-ETH v2.7.0 — finite D.4.4 weighted-tile modes

Cumulative upgrade of v2.6.0. Adds `eth_modes_v27` implementing finite scalar Cauchy geometric column-tile modes using independently checked D.3 packet input, 2-adic coefficient valuations, exact rational coefficients, modular pruning, lazy weighted tuple enumeration, a genuinely separate reconstruction checker and a full small-network deformation/expansion oracle. Includes isolated API/CLI/browser interface, tests, documentation, and a reproducible benchmark.

**No full ETH algorithm is claimed:** extension-field Taylor jets, specialized implicit child tensors, tapered interpolation integration and subexponential recursive contraction remain missing. See `docs/D44_FINITE_MODES_V27.md`.

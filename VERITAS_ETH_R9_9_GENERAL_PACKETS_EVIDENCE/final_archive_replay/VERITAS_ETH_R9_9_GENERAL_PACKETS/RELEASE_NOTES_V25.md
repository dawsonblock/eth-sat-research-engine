# VERITAS-ETH v2.5.0

## Added

- Explicit exact-manuscript versus experimental-scaled parameter modes.
- Endpoint-load conditional-expectation symbol assignment.
- Real-wire preserving, orientation-aligned packet embedding.
- Independent certificate checker for slot alignment, packet count and
  symbol load. Reports failed numerical bounds instead of claiming success.
- GF(2) irreducible polynomial construction and testing.
- Exact 2-adic extension ring plus truncated polynomial jets, both with unit
  inversion and nonunit detection.
- Exact local Cauchy polynomial `W(0)=I` reference.
- Separate `veritas-eth25` CLI, FastAPI routes, browser controls and tests.

## Preserved

Everything from v2.4.0, including SAT/#SAT, component-DAG and weighted
proof certificates, posterior marginals, generic tensor contraction,
Cauchy/Hermite experimental references, existing APIs and CLI.

## Exclusions

The manuscript D.3 collision-packing theorem, complete finite-ring
interpolation and specialized D.4.4 recursion remain OPEN. No
subexponential result is claimed for this software.

See `docs/ETH_V25_MATHEMATICAL_SCOPE.md` and `RELEASE_REPORT_V25.md`.

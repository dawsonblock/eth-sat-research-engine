# VERITAS-ETH v2.6.0 release notes

- Preserves all v2.5 source, older routes, exact-counting backends and research implementations.
- Adds `eth_packing_v26` to implement **directed pair-label conditional expectation**, independent row/column vertex labels and full common-H packet embedding.
- Adds an independent D.3 replay checker, including conditional-score transcript replay and a uniform capacity census over *all* directed label classes.
- Corrects v2.5 Appendix D parameter rounding (floor -> ceiling) and removes its unsupported claim that `u_d>0` alone establishes eligibility. Complete theorem eligibility is still **not** asserted.
- Adds two API routes, a status endpoint, `veritas-eth26` CLI, a web-console section, adversarial tests, a seeded validation script and a benchmark.
- A certified *finite numeric D.3 layout* is not a proof that specialized recursion is implemented, or that #SAT is subexponential.

See `docs/ETH_V26_D3_MATHEMATICAL_SCOPE.md` and `RELEASE_REPORT_V26.md` for detailed scope, validation and limitations.

The 128-edge D.6 demonstration uses scaled `r=2`, **not** the paper’s fixed `r=64` schedule; it proves only finite numeric invariants.

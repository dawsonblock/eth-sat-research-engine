# VERITAS-ETH v2.8.0 — release notes

Full cumulative upgrade over v2.7.0. Retains previous SAT/#SAT, proof-certificate, conditional probability, symbolic reasoning, D.3 finite packing, D.4.4 scalar modes, API and CLI.

## New
- Corrected published Appendix D floor parameters; numerical eligibility only; unpinned-source warning.
- Canonical distinct GF(2^e) residue-point generator with validation.
- Exact polynomial interpolation in `R_p[z]` via only unit denominators and independent sample replay.
- Immutable creation-time canonical tensor-entry lift class, with non-homomorphism tests.
- Shifted Cauchy polynomial coefficient arithmetic via exact rational cancellation; rejects even denominators before ring mapping.
- Complete finite Cauchy shifted-jet validation for all packet entries with extension-ring interpolation.
- New CLI `veritas-eth28`, REST endpoint `/v1/research/eth/extension-cauchy`, local UI panel, and mathematical regression tests.

## Not implemented
- The manuscript-specific tapered Hermite recovery.
- Extension-ring weighted D.4.4 tensor modes.
- Specialized implicit child-tensor construction and recursive subexponential contraction.
- Immutable commit pin or formal software-to-proof correspondence.

The package must NOT be described as an ETH-breaking solver. Use `RELEASE_REPORT_V28.md` for empirical test evidence.

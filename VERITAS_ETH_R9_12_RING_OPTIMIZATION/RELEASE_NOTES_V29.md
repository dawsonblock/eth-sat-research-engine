# VERITAS-ETH v2.9.0 — release notes

Cumulative source upgrade from v2.8.0. **This is NOT a completed ETH-breaking solver.** No algorithm in this release is claimed to run in subexponential time on arbitrary SAT instances.

## New implementation

1. `eth_interpolation/tapered_hermite.py`: a bounded, exact finite **reference** for the manuscript's valuation-dependent `q_t` / `p_t` schedule. It builds the confluent Hermite constant-term functional with exact rational elimination and uses coefficient-specific 2-adic input-precision requirements. Different interpolation nodes supply *different* modulus sizes. Invalid or insufficient residue data fail closed. Includes an independent known-polynomial replay oracle.
2. `eth_modes_v29/extension_modes.py`: exactly evaluates full Cauchy coefficient **jets over** `(Z/2^p)[U]/f(U)` and provides a checked finite rank-one factorization of *cross-group* interactions. Each mode reports actual minimum coefficient 2-adic valuation. Modes identically zero at the working precision can be safely omitted. A checker reconstructs every cross-group jet directly from the original Cauchy polynomial and rechecks D.3 certificates, incidences, valuation metadata and coefficient encodings.
3. New `veritas-eth29` CLI; POST `/v1/research/eth/tapered-reference`, POST `/v1/research/eth/extension-modes`, POST `/v1/research/eth/extension-modes/check`, GET `/v1/research/eth/v29/status`; local UI panels.
4. Added independent adversarial tests and seeded validation script `scripts/validate_v29.py`.

## Non-implemented / required for stronger claim

- The v2.9 rank-one column-mode decomposition is **not** the manuscript's D.4.4 geometric tile-mode expansion in the full extension-jet coefficient ring; it has no matching asymptotic retained-mode bound.
- The tapered recovery uses a bounded `degree<=31` exact rational linear system, **not** the manuscript's complexity-optimal interpolation routine or proof.
- The specialized implicit recursive child tensors, their subnetwork bounds, and end-to-end ETH recurrence are still absent.
- The public manuscript has **not** been pinned to an immutable Git commit in this archive.

## Validation

From project root: `python -m pytest -q`, `python scripts/validate_v29.py`, `python scripts/validate_10000.py`, `python scripts/smoke.py`. Run `python scripts/build_release.py` then `python scripts/verify_manifest.py`. The release report records the executed counts and platform.

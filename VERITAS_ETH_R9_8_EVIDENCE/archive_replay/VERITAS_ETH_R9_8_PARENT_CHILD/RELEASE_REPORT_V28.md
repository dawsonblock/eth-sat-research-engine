# VERITAS-ETH v2.8.0 — test and implementation audit

## Release scope

Cumulative upgrade from v2.7.0. New functionality: corrected published floor-based `u_d`; exact residue-separated 2-adic extension-ring interpolation and evaluation; canonical creation-precision tensor entry representatives; shifted local Cauchy coefficient interpolation; API, CLI, UI, reproducible tests.

The published manuscript was inspected via the mutable `main` source link on 2026-10-31. **No immutable commit SHA was obtained**, so this is not a commit-pinned proof reproduction. See `docs/SOURCE_REVISION_DIFFERENCES_V28.md`.

## Executed validation — Linux, Python 3.13.5

- `PYTHONPATH=src python -m pytest -q`: **398 tests passed**.
- `PYTHONPATH=src python scripts/validate_v28.py`: **1,536 seeded exact polynomial recovery checks** and **146 shifted Cauchy matrix entry reconstructions** passed.
- `PYTHONPATH=src python scripts/validate_10000.py`: **10,000 random CNF instances** with independent reference count/SAT agreement; 106 tensor vs exhaustive comparisons.
- `PYTHONPATH=src python scripts/validate_v27.py`: **125 scalar mode certificate checks** and **60 small full-scalar identities** passed.
- `PYTHONPATH=src python scripts/smoke.py`: split-wire, #SAT, tensor, entailment, and certificate smoke checks passed.
- FastAPI `TestClient`: GET v2.8 status, successful POST extension-Cauchy, invalid insufficient-degree POST returning HTTP 422.
- `veritas-eth28 cauchy --packet-size 4 --node 1 --precision 8 --extension-degree 4`: all 16 local Cauchy matrix entries reconstructed.

## Mathematical audit conditions

1. `interpolate_newton` verifies every sample, and inputs with duplicated residue classes are rejected even when represented by different higher-precision coordinates.
2. `shift_cauchy_entry` obtains rational coefficients and checks exact 2-adic integrality before ring reduction; no inverse of an even denominator is permitted.
3. `CreationEntry` stores creation precision and coefficients; tests show explicitly that canonical lifting is not a ring homomorphism.
4. No claims are made for the tapered Hermite algorithm, full ring-valued D.4.4 modes, child-tensor recursion, space bounds or subexponential time.

## Security and reliability

All research methods are bounded. Invalid interpolation points, parameter values and precision configurations fail closed. Numeric `eligible` for parameter checks means *only* that selected packing inequalities are satisfied, never that the full theorem is established.

## Future gates

M3 — tapered finite-ring Hermite with guard precision; M4 — ring-valued D.4.4 modes; M5 — implicit specialized children; M6 — correct end-to-end recursion; M7/M8 — independent bit-complexity and polynomial-space proof review. These are not implemented.

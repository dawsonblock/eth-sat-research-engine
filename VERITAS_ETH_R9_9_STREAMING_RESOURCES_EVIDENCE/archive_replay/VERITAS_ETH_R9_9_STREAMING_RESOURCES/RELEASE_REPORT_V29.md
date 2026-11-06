# VERITAS-ETH v2.9.0 — release validation and mathematical scope

## Provenance and contents

Cumulative release from local `VERITAS_ETH_v2.8.0_FULL_UPGRADED.zip`. All existing source functionality retained. The added components are a **bounded finite reference**, not the paper's complete recursive D.4.4 algorithm. Public manuscript commit remains unpinned.

## New components

- `eth_interpolation/tapered_hermite.py`: node-dependent `q_t` and `p_t` formulas with exact rational Hermite recovery from per-node residues and coefficient-specific guard requirements. Includes independent known-polynomial replay; degree bound <=31.
- `eth_modes_v29/extension_modes.py`: actual Cauchy coefficient Taylor jets over a 2-adic extension ring, exact rank-one cross-group factorization and independent coefficientwise valuation and matrix-identity checking. **Not** manuscript geometric tile modes.
- CLI `veritas-eth29`, API and local browser console; backward compatibility with inherited routes.

## Executed validation (Linux, Python 3.13)

- `PYTHONPATH=src python -m pytest -q`: **426 tests passed**.
- `PYTHONPATH=src python scripts/validate_v29.py`: **240** seeded exact tapered-Hermite polynomial recoveries, **288** extension-mode certificate cases, **720** independent rational Cauchy entry evaluations passed.
- `PYTHONPATH=src python scripts/validate_10000.py`: **10,000** CNF count and satisfiability comparisons and **106** tensor-vs-exhaustive comparisons passed.
- `PYTHONPATH=src python scripts/validate_v28.py`: **1,536** inherited polynomial-recovery and **146** Cauchy entry checks passed.
- `PYTHONPATH=src python scripts/validate_v27.py`: **125** mode-certificate and **60** full scalar identities passed.
- `PYTHONPATH=src python scripts/smoke.py`: existing split-wire, counting, tensor, entailment and proof-certificate smoke checks passed.
- Tampered rational-jet oracle data, missing modes, wrong coefficients, altered ring metadata, invalid packet input and false scope claims are rejected by the new checker tests.

## Claims expressly NOT supported

- The new finite extension-ring rank-one modes **are not the manuscript's weight-counted geometric-tile expansion**; they do not certify the manuscript's mode enumeration bound.
- The tapered recovery uses a bounded rational solve, not an efficient arbitrary-size Hermite algorithm with proven complexity.
- No implicit manuscript child-tensor network or paper-specific subexponential recursive contraction has been implemented.
- No end-to-end asymptotic ETH or polynomial-space result has been reproduced in software.

## Artifact integrity

The generated ZIP is reproducible with `python scripts/build_release.py`. The SHA-256 manifest certifies bytes included in the package, **not** source authorship or cryptographic provenance. The archive is separately extracted, checksum checked, and tests rerun in the final release verification step.

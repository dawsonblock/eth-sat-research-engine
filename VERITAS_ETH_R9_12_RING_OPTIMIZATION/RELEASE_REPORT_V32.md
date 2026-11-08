# VERITAS-ETH v3.2.0 validation report

Status: source-level and finite-reference release. This report is updated
from actual test and packaging results; no theoretical performance claim.

Tests:
- New `test_v32_mode_bonds.py`: 4 tests passed (direct mode-bond identity, certificate tampering, 24 seeded random trials, API and resource caps).
- End-to-end independent random/differential script: `validate_v32.py` — 40 seeded cases passed, matching v3.1 and independent full half-edge contraction, with tampering rejected.
- Existing v3.0 and v3.1 tests rerun; selected cross-version run passed 19 tests.
- Complete cumulative project regression: **445 tests across 59 modules reached 100% without failures**, see `validation/v32_pytest_full.log`.
- Extracted archive SHA-256 manifest verification and executable smoke check (see final archive validation).

Correctness scope: finite exact mode-index contraction and independent Cauchy
half-edge cross-check. No manuscript-specific asymptotic proof and no
verified D.4.4 recursive packet tensors.

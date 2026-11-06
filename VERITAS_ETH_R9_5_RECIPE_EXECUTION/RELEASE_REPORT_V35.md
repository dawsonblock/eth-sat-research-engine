# VERITAS-ETH v3.5.0 — finite exact child-scope audit

## Changes

Full cumulative v3.4 source plus an independently replayable v3.5 finite
child-network scope ledger. It enumerates **all original Boolean half-edge bits**,
**both endpoints of every cross-group mode bond**, original factor ownership,
local factor port scopes, and actual sparse mode-bond group tensor cardinalities.

A numeric `max_child_scope` guard performs a structural preflight **before**
expensive exact group tensor construction. The certificate checker replays D.3
packing, finite Cauchy modes, the v3.3 recursive contraction, the v3.2
independent sparse elimination, and an independent direct half-edge oracle.

## Validation

- v3.5 unit tests: 12 passed in local targeted run.
- v3.4/v3.5 targeted combined tests: 18 passed.
- `scripts/validate_v35.py`: 35 seeded exact reconstructions and tamper checks passed.
- `scripts/validate_10000.py`: 10,000 baseline differential cases and 106 tensor comparisons passed.
- `scripts/smoke.py`: passed.
- Full inherited regression run (before the final API-only test was added): exit code 0, all collected tests passed.
- All 12 new v3.5 tests including FastAPI round-trip: passed.
- Full final 470-test suite: all passed, process exit code 0 (`PYTHONPATH=src pytest -q --durations=5`).
- Windows PowerShell launcher included, not executed in this Linux environment.

## Explicit limitations

The finite child index scope is NOT the manuscript's D.4.4 recursively
constructed packet-tensor network wire count. This release does not establish
`M_child < M/8`, polynomial space for the paper-specific recursion, or
subexponential SAT/#SAT time. Existing finite implementations remain subject
to exponential worst-case complexity. Manuscript source commit is not pinned.

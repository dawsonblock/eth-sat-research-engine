# General finite shrinking recursion

Commit `9cd389dd658d4d16c6cf2f171052297f271e5a9a` on `dev/r9.8-general-recovery`. Source binding `a9e706bd9724da766e8e87eb93f81b4d6ecb077c0c2c513c50b8872cecea3d76`.

Implemented full interpolation, exact coefficientwise Hermite recovery, nonzero singleton point modes, checked 64-child recursion, and bounded high-precision coefficient encoding. Legacy constant-row and depth-limited drivers remain separate.

The nonconstant matching case computes `(24+7*W_xx(T))^22` at 134 points and recovers `31^22` exactly: 22 -> 2 edges, 8,577 calls, 1,536-bit point arithmetic, zero nonshrinking children. This validates one active general level. Nonzero cross-mode identities are tested separately; a complete general run with nonzero crossing modes and a nonconstant two-active-level run remain unestablished.

Validation: 1,689 effective passing test cases, two optional pybind skips, no unresolved failures. The raw full suite had one Lean-launcher environment failure; the exact case passed with the pinned compiler. Both attempts are preserved in `pytest_summary.json`. All 12 inherited validators, all 41 Lean module/axiom audits, and all 16 portable commands passed. New general execution passes in a clean Python 3.10.19 wheel and Docker Python 3.12.14. Docker uses no network, two CPUs and 1 GiB.

The connected 484-edge layout requires 22 weight-one modes at zeta=1 and approximately 8.16e77 complete tuples. Its generic grid requires 1,453 points per node and extension degree at least 11. The preflight correctly refuses it; higher wire caps do not resolve that cost.

Everything remains FINITE_SCALED_EXPERIMENT. Source padded packet bounds fail on the fixtures; source qualification, universal executable refinement, general source execution, and bit-time/peak-space proofs remain unestablished. No new general-driver Lean theorem, standalone saved recursive-trace verifier, full-container pytest, or hosted CI is claimed.

See `verification.json`, `general-validation.json`, `connected484-general-preflight.json`, and the source guide `docs/R98_GENERAL_SHRINKING_RECURSION.md`. The source ZIP and extracted tree both passed the complete 1,095-file manifest check. The sealed R97 and R98 baselines still match their original manifests.

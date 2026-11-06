# Configurable finite shrinking groups

Commit `4fb5a5cf848664e4c3d3afea4a12b780080ee1fd` on `dev/r9.8-configurable-groups`. Package source binding: `dc674b6f9c193ba32845b827c85ff644a662e765ba3e1a95a8619f9d2e7d3ec9`.

Both finite drivers now accept a fixed group count from 64 to 1,024. The default and manuscript source count remain 64. An independent preflight uses graph incidence, without tensor values, to check every projected descendant down to four-edge leaves. It checks complete tuple counts, calls, precision, depth, work/time and evidence budgets. Every actual child must match the projected topology before recursion. All children, including empty units, are recomputed; no oracle supplies a production answer.

Validated external CLI cases:

- Constant 484-edge cycle, 512 groups: 484 -> 4 edges, 1,025 calls, 31,488-bit points, exact result 2^484.
- Constant 1,000-edge cycle, 1,024 groups: 1,000 -> 4 edges, 2,049 calls, 65,024-bit points, exact result 2^1000.
- Nonconstant 22-edge matching, 65 groups: 22 -> 2 edges, 134 points, 8,711 calls, exact result 31^22.
- The 484-edge cycle with 128 or 256 groups refuses un-packable descendants before production calls.
- The 484-edge cycle with 1,024 groups refuses degree-two vertices because its per-side capacity is one.
- The 512-group cycle refuses a total call budget of 1,024 before production calls.
- The general 484-edge cycle with 512 groups refuses its complete tuple count: 242 crossing modes and binomial(31729,242) retained tuples at a nonzero point.

Separate mode evidence checks one retained tuple with source group 64 in a 128-group layout. It does not claim complete point recursion. The inherited default 64-group two-level cases remain passing.

Validation: 1,765 effective passing cases, two optional pybind skips, and no unresolved failures. The raw full suite had one obsolete error-message assertion. That test was strengthened to require depth refusal before production calls; it and 42 related cases passed on retry. Production package bytes did not change. Both attempts are preserved in `pytest_summary.json`.

All 12 inherited validators, all 41 Lean module/axiom audits, and all 18 portable commands passed. The new 512-group execution and refusal cases passed in a clean Python 3.10.19 wheel and Docker Python 3.12.14. Docker used no network, two CPUs and 1 GiB memory.

All new work remains FINITE_SCALED_EXPERIMENT. The source schedule and paper bytes are unchanged. Source padded packing bounds fail on these singleton fixtures. Source qualification, new formal refinement, universal Python correspondence and bit-time/peak-space bounds remain unestablished. Saved traces still lack a standalone independent recursive consumer. Hosted CI and full-container pytest were not run.

The development archive and a freshly extracted tree passed the complete 1,102-file manifest check. The sealed R97, R98 and GENERAL baselines passed their original manifests. See `verification.json`, `groups-validation.json`, and the source guide `docs/R98_CONFIGURABLE_FINITE_GROUPS.md`.

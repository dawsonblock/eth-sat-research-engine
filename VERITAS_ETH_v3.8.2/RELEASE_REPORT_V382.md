# VERITAS-ETH v3.8.2 historical report and R8.1 validation refresh

The original v3.8.2 report recorded 522 tests on Python 3.12.0 and 3.10.19
for an earlier source snapshot. That historical result is not a test result
for the current R8.1 working tree.

## Fresh dense-Cauchy validation

The current `scripts/validate_dense_v382.py` was run with its defaults on
Python 3.12.0. Its regenerated output is
[`validation/r81_dense_cauchy.json`](validation/r81_dense_cauchy.json),
SHA-256 `6f6a2d3bc548f27b8ea780ab6b0675c41f9739fecdd55aa4bb6b718560192a81`.
The seeded reconstruction results are:

| Wires | Status | Guard bits | Counted scalar operations |
|---:|---|---:|---:|
| 8 | EXACT_HERMITE_RECONSTRUCTION_CHECKED | 13 | 579,584 |
| 10 | EXACT_HERMITE_RECONSTRUCTION_CHECKED | 17 | 4,033,536 |
| 12 | EXACT_HERMITE_RECONSTRUCTION_CHECKED | 21 | 24,813,568 |
| 14 | BLOCKED_RESOURCE_LIMIT | — | — |
| 16 | BLOCKED_RESOURCE_LIMIT | — | — |

The eight-wire case includes six independent half-edge jet-evaluation checks.
The scalar counters omit matrix and exact rational plan construction,
validation, modular-reduction bit costs and the independent jet oracle. They
are finite scoped measurements, not complete work or memory bounds.

The prior [`validation/v382_dense_cauchy.json`](validation/v382_dense_cauchy.json)
is preserved as historical evidence, SHA-256
`eb39feae37f33615e4a4ce2275ee678ed0204560a7d2598c8dad9ee83b776854`. Its old
8- and 10-wire operation counts and 12-wire resource outcome do **not**
describe the current script's output. The precise cause of that historical
difference was not independently established.

## Qualification boundaries

The separate eight-wire tapered-recursion experiment has a different input,
algorithm, counters and evidence record; its numbers must not be compared as
if they were the dense-Cauchy measurements above. See
[`docs/TUPLE_STREAM_R81.md`](docs/TUPLE_STREAM_R81.md) for the current tuple
stream repair and its finite scope.

Hosted CI, independent proof review, the theorem-mode recursive construction,
universal child shrinking, the asymptotic runtime and polynomial space remain
**NOT EVALUATED / NOT IMPLEMENTED**. The source pin and finite tests are not
independent verification of the manuscript's proof.

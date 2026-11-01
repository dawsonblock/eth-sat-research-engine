# v3.8.2 validation report

## Local evidence

- Full source test suite: **522 passed** under Python 3.12.0 and Python
  3.10.19. Tests were run after the reconstruction and independent-jet checks
  were added.
- Focused v3.8 child-elimination validation: **40/40** exact finite
  oracle/certificate comparisons passed.
- `scripts/validate_dense_v382.py`: completed seeded cases at 8, 10, 12, 14,
  and 16 wires. Nonzero-node Hermite reconstruction passed at 8 and 10 wires;
  the 8-wire case also passed six independent half-edge jet-evaluation
  checks. The 12-, 14-, and 16-wire reconstructions returned
  `BLOCKED_RESOURCE_LIMIT` before running the transforms.
- The 8-wire reconstruction used 13 guard bits and 2,501,120 counted scalar
  operations; the 10-wire reconstruction used 17 guard bits and 15,913,472
  counted scalar operations. These counters omit matrix construction, exact
  rational plan construction, validation, modular-reduction bit costs and
  the independent jet oracle.
- Validation artifact:
  `validation/v382_dense_cauchy.json`, SHA-256
  `eb39feae37f33615e4a4ce2275ee678ed0204560a7d2598c8dad9ee83b776854`.
- The source-pinned manuscript identity is inherited from v3.8.1; its pin is
  not independent verification of the manuscript proof.

## Release and remaining gates

Archive SHA-256, byte count, package manifest verification in normal and
optimized Python, extracted-archive checks, and source identity are recorded
in the sibling `VERITAS_ETH_v3.8.2_RELEASE_EVIDENCE.txt` file.

Hosted CI, Linux execution, independent mathematical review, full D.4.4
recursion, the universal child-size bound, asymptotic runtime, and polynomial
space remain **NOT EVALUATED / NOT IMPLEMENTED**. This candidate is not a
qualified release or a universal SAT solver.

# VERITAS-ETH v2.7.0 — Release validation

Source: cumulative upgrade of `/mnt/data/VERITAS_ETH_v2.6.0_FULL_UPGRADED.zip` (original code preserved and extended).

## Added modules

- `eth_modes_v27/constructor.py`: finite scalar geometric column tile expansion on independently checked D.3 packets.
- `eth_modes_v27/checker.py`: independent reconstruction of the Cauchy kernel mod 2^p and mode valuation/integrity checks.
- `eth_modes_v27/enumeration.py`: bounded lazy exponent enumeration and exact weighted tuple count.
- `eth_modes_v27/reference.py`: complete tiny-network contraction identity comparison.
- `eth_modes_v27/cli.py`: mode certificate construction, replay, and tuple-count tool.
- API, UI, docs, tests and benchmarks.

## Recorded checks

- **368 pytest tests passed** including the full inherited suite, using `PYTHONPATH=src pytest -o addopts='' -q`.
- **125** additional seeded finite D.4.4 mode-construction/independent checker cases passed, using `python scripts/validate_v27.py`.
- **60** additional complete small deformed-network contraction-vs-mode expansion checks passed.
- Tampered row coefficients, weights, tile columns, D.3 wire identities, weighted-tuple counts, node parameters and inflated theorem claims rejected in regression tests.
- Checked nontrivial degree-b≥1 geometric modes on a 12-wire finite example.
- Source `compileall` passed.
- All arithmetic is exact in the supported scalar-integer evaluations; no floating-point tolerances used.

## Limited reference performance

The 4-wire/12-wire diagnostic benchmark records 2/10 retained modes and 15/115 weighted exponent tuples at precision 5 respectively. Execution durations are platform-specific and are **not** evidence of asymptotic improvement.

## Scientific scope

This release does NOT implement the full D.4.4 extension-ring Taylor jets, tapered Hermite integration, implicit recursive group child tensors, or the paper's subexponential recurrence. The original paper's D.3 numeric preconditions are reported separately and are usually not satisfied in these deliberately small examples.

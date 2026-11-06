# VERITAS-ETH v3.4.0 — independently checked structural child-topology upgrade

## Scope

A full cumulative release of v3.3 plus a D.3 real-half-port/symbol-group
ledger, packet-slot incidence certification, independently checked finite
geometric-mode source/target incidence, and a source-replayed bridge binding
these indices to existing finite exact v3.3 recursive mode-bond contraction.

This release **does not** implement the manuscript-specific shrinking child
packet tensor networks, prove `M_child < M/8` for full child networks, or
establish subexponential runtime. The finite `H_g <= 6M/r` inequality is
an original-half-port statement, not a guarantee on total child wires.

## Testing in current Linux container

- `PYTHONPATH=src pytest -q --durations=10`: all **458** collected tests passed, process exit code 0. The slowest test took 5.10 seconds.
- `PYTHONPATH=src pytest -q tests/test_v34_child_topology.py tests/test_v34_bridge.py tests/test_v33_recursive_bonds.py tests/test_v32_mode_bonds.py tests/test_v31_geometric_jet_children.py`: 23 tests passed.
- `PYTHONPATH=src python scripts/validate_v34.py`: 45 randomized D.3 ledger cases and 12 source-checked finite composite contractions, plus tamper rejection.
- `PYTHONPATH=src python scripts/validate_10000.py`: 10,000 independent SAT/count comparisons and 106 tensor comparisons passed.
- `PYTHONPATH=src python scripts/smoke.py`: passed.
- `python -m pip install --no-deps --no-build-isolation -e .`: installed successfully; `veritas-eth34 construct`, `contract`, and `check` passed.

## Final package checks

- First packaged ZIP: integrity tested without errors.
- All 339 release-file SHA-256 hashes matched, with no unlisted files.
- Independently extracted archive: all 339 hashes verified; 13 targeted v3.4/v3.3 tests, the 45-case structural validation and the startup smoke script passed.
- Archive was regenerated after this report update, then checked again.

## Caveats

- Verification occurred on Linux with Python 3.13. Windows launcher included but not executed on Windows.
- Ordinary `pip install -e .` requires Python package-index access for isolated build dependencies; that was unavailable in the container. Local installation succeeded with `--no-build-isolation`.
- The published manuscript source commit is not immutably pinned in the package. The implementation should not be described as a fully matched mathematical reproduction.
- These are finite implementations and tests, not a proof of the paper's theorem.

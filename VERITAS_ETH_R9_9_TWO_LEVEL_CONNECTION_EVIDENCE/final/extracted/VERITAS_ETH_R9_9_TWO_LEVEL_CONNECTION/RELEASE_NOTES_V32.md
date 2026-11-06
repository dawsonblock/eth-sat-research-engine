# VERITAS-ETH v3.2.0 — Sparse geometric-mode bond tensors

Full cumulative upgrade from v3.1.0, retaining previous solvers, mathematical
research modules, API, UI, CLI, and regression tests.

**New:** exact source/target group transfer tensors indexed by geometric
mode-exponent bonds. Contraction uses sparse indexed joins and exact summation
over shared exponent indices, rather than enumerating every full global
mode-exponent tuple. Each certificate exposes child table entries, modes,
exact truncated extension-ring coefficients, resource usage, and an
independent 4^M half-edge count comparison. New checker replays results from
original formula and geometric mode construction, detecting tampering.

* Modules: `src/veritas/research/eth_mode_bonds_v32/`
* Command: `veritas-eth32`
* API: `/v1/research/eth/mode-bond-network`, `/check`, `/v32/status`
* UI: v3.2 mode-bond demonstration
* Tests: `tests/test_v32_mode_bonds.py`, `scripts/validate_v32.py`
* Mathematical details: `docs/MODE_BOND_TENSOR_NETWORK_V32.md`

**Not implemented:** recursively shrinking manuscript D.4.4 packet-tensor
construction; claimed M/8 bound; subexponential algorithm. Do not treat
this version as a theoretical proof or general-purpose fast #SAT solver.

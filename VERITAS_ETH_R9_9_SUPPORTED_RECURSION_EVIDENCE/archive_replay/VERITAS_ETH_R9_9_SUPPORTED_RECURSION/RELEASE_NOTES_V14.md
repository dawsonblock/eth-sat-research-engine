# v1.4.0 upgrade release notes

- Added `src/veritas/research/bounded_degree.py`: exact CNF to degree-3
  variable COPY gadgets; supports repeated-literal, unused-variable,
  empty-clause and high-incidence cases.
- Added `src/veritas/research/minfill_contract.py`: deterministic exact
  contraction, modular arithmetic and fail-closed work/time/table budgets.
- Added `POST /v1/research/bounded-degree-tensor` with optional independent
  count checking, local audit record, input hash, stats, and error statuses.
- Added CLI `--bounded-degree`, `--gadget-contract` and resource arguments.
- Added two browser operations, a proof explanation, adversarial tests and
  an 800-case seed-pinned differential validation script.
- Preserved the full v1.3.0 source, API and existing mathematical modules.

The degree-reduction construction is *parsimonious* and linear-size for
fixed clause width. It does not perform ETH paper D.4.4 recursive weighted
mode packing or improve the proven worst-case counting complexity.

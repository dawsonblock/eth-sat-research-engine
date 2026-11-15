# DIMACS fixtures for residual-state benchmarks

Place archive or network CNFs here (DIMACS `p cnf` format). Files are auto-discovered by:

- `benchmarks/v34_residual_growth.py`
- `benchmarks/v36_backend_comparison.py`
- `scripts/validate_residual_gates.py`

Constraints:

- `n ≤ 22` for residual metrics and dual-backend gates (configurable via API flags).
- UTF-8 text; extension `.cnf`.

Shorthand names in reports: `dimacs_<filename_stem>`.

To validate after adding files:

```bash
export PYTHONPATH=src
python benchmarks/v34_residual_growth.py
python benchmarks/v36_backend_comparison.py
python scripts/validate_residual_gates.py
```

Optional per-case compression floors without code changes: edit
`validation/residual_compression_floors.json` (merged over Python defaults).
# R9.10 finite numerical evidence

These certificates require the co-delivered R9.10 source archive. Source qualification and theorem mode remain disabled. The complete resource contract is partial: bit operations are not instrumented, and time/space theorems are unproved.

From the extracted source checkout, independently replay either run with:

    PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli examples/r910_matching235.json --layout-file examples/r910_matching235_layout.json --replay-dir /path/to/evidence/numerical/run --output-dir /new/external/replay235

    PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli examples/r99_nonconstant_matching242.json --layout-file examples/r99_nonconstant_matching242_layout.json --replay-dir /path/to/evidence/numerical242 --output-dir /new/external/replay242

Outputs must be new external directories. `report.json` binds the implementation source and event stream. The checker reconstructs dependencies and numerical contributions; the hashes alone do not prove correctness. `reference.json` records the independent matching-edge integer calculation. The source release report explains the exact zero-tail optimization and remaining obligations.

`validation_summary.json` summarizes the gates. Environment and artifact hashes accompany the results. Times and RSS describe these runs, not universal resource bounds. Historical absolute paths in command logs identify the originating checkout; use the relative reproduction commands above on another machine.

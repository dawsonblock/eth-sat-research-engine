# Bounded source-entry and leaf API

The schema `VERITAS_SOURCE_ENTRY_V1` binds `kind`, `arity`, `creation_precision`, `polynomial`, `jet_length` and `data` in canonical ASCII JSON: sorted keys, no whitespace, no duplicate keys, no floats, canonical nonnegative coordinates. The frozen `SourceTensorReference` also binds this metadata and hashes the exact bytes. JSON object reordering is intentionally rejected for this recipe-byte format (unlike the separate V3 transcript canonicalization policy).

Kinds:

| Kind | Data and index convention |
|---|---|
| `dense` | `2^arity` jets, in lexicographic order of the port bit tuple; each jet is exactly `ell` rows of `e` canonical integers |
| `equality` | Empty payload, positive arity; all input bits must agree |
| `clause` | One polarity per port: 1 means positive literal, 0 means negative; empty clause is zero |
| `packet` | `[row_positions, column_positions, local_matrix, target_modes, source_modes]` |

Packet positions partition all ports. The local matrix has one creation-ring jet per row/column pair. Each target is `[beta, coefficients_per_row]`; each source is `[beta, integer_coefficients_per_column]`. Mode positions identify formal variables; equal supports do not merge distinct variables. Beta-zero target variables may be omitted during coefficient extraction because each row factor is affine and only nonnegative exponents occur. Empty and impossible coefficients have their exact algebraic semantics. The kernel does not certify weights or source-mode completeness.

Example, run with `PYTHONPATH=src`:

```python
from veritas.research.tapered_v4.source_recipes import make_reference, evaluate_source_entry

entry = make_reference(
    kind="packet", arity=3, creation_precision=3,
    defining_polynomial=7, jet_length=1,
    data=[[0], [1, 2], [[[[6, 0]], [[6, 0]]]], [], []],
)
result = evaluate_source_entry(entry, (1, 1, 1), precision=7)
assert result["result"] == ((4, 0),)  # compute modulo 8 before lifting
```

`source_node_from_described(network, context, depth=..., precision=...)` converts existing immutable descriptions, preserving creation precision and the old dense bit order. The supplied `SourceContext` must satisfy admission; this bridge does not generate or certify recursive ancestry.

`contract_source_leaf(node, SourceLeafPolicy(verify_independent=True))` returns `EXACT_SOURCE_LEAF_MODULAR_CONTRACTION` only on full success. Source-active calls, theorem requests, unsupported recipes, invalid root coefficients, failed checks and exhausted budgets have an explicit inconclusive status and no `result` field. The optional oracle must check the entire leaf or reject; there is no partial-coverage success. It never supplies the production answer. Low-level `CompiledEntry` objects are internal validated intermediates, not an external certificate API.

Reproduction:

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
PYTHONPATH=src python -m pytest -q -o addopts='' tests/test_r95_source_recipes.py tests/test_r95_source_leaf.py tests/test_r95_hermite_grid.py
python scripts/validate_r95_recipes.py
python scripts/validate_conditional_expectation_lean.py --output validation/r9_5_proof_gate.json
PYTHONPATH=src python -m pytest -q -o addopts=''
```

The evidence runner measures RSS on macOS/Linux; it is not a sandbox. No arbitrary-density reduction or theorem runtime qualification is provided by this API.

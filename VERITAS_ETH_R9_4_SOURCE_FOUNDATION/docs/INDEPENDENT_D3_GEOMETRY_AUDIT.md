# Finite sparse packet geometry and load audit

`audit_sparse_packet_geometry` independently checks an explicitly supplied
labeled graph and sparse packet assignment. It does not require those labels
to have come from the project's deterministic conditional-expectation
constructor. This broadens the scope of finite *geometry auditing*, not the
inputs accepted by the recursive contraction engine.

The separate opt-in `geometry_point` module uses that audit to generate and
replay finite point modes for noncanonical sparse packet sources. It can
construct their bounded children and compare their complete point expansion
with the independent direct half-edge oracle. The canonical point API and
recursive engine still require the deterministic-source replay by default.
The same opt-in path can certify and replay a Hall-zero witness from checked
mode supports and compare a selected tuple with the independent direct
half-wire and row-selection oracle. Such a zero is an exact finite result,
not evidence of a universal bound on how many terms can be removed.
The opt-in path has the existing finite wire, precision, tuple and mode caps;
its geometry-work cap is a coarse per-audit bound, not a hard global
bit-work, wall-time or memory limit. Exhausted budgets do not yield a
partial count. A point-identity check does not establish tapered recovery or
the uniform theorem.

The auditor checks the dimensions and uniform padding, vertex-label coverage,
packet address uniqueness and bounds, real-slot uniqueness, orientation at
every coordinate, and exact coverage of all real parent edges. It derives
each coordinate's row and column symbol loads directly from parent endpoints.
Each reported predicted child wire count is their sum; the report also checks
the per-side `3M/r` condition and the resulting `6M/r` bound for every
group. These predictions apply to a child construction having exactly one
wire per assigned half-edge and no extra wires; the auditor does not inspect
such a child or establish its tensor identity.

This procedure checks one supplied finite packet source. It neither verifies
the source's conditional-expectation trace nor proves that a suitable
assignment exists for arbitrary networks, and it does not integrate a new
theorem-mode execution path. The cooperative `max_work` guard is a coarse
item/coordinate limit, not a hard memory, elapsed-time, or bit-operation
bound. A source satisfying the geometry may still fail the D.3 numeric
conditions or fail to be accepted by the existing deterministic-replay mode
generator. The reported numerical condition uses the actual maximum degree;
the auditor does not try alternative larger declared degree bounds.

## Reproduce the noncanonical L=8 example

Run this snippet from the project root. The selected tuple has weight seven
at precision eight; its coefficient is zero by a Hall deficiency, confirmed
by an independent direct tuple oracle. The complete 23-tuple point expansion
also matches the separate direct half-edge contraction. The packing is
finite and noncanonical and is not part of the manuscript's parameter
schedule.

```python
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import SPARSE_MODE_SCHEMA
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.geometry_point import (
    make_geometry_point_modes, certify_geometry_point_matching_zero,
    replay_geometry_point_matching_zero, direct_geometry_tuple_contribution,
    contract_geometry_point_expansion,
)

source = {
    'schema': SPARSE_MODE_SCHEMA,
    'claim': 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS',
    'r': 2, 'a': 3, 'L': 8, 'D': 64, 'M': 2, 'H_pad': 8,
    'edges': [[0, 0], [1, 1]],
    'row_labels': {'0': [1, 0, 0], '1': [0, 0, 1]},
    'column_labels': {'0': [0, 1, 1], '1': [1, 1, 0]},
    'packets': [{'symbol_pairs': [[0, 1], [0, 1], [0, 1]],
                 'index': 0, 'occupied_slots': [[1, 0], [4, 1]]}],
}
parent = describe_integer_network(from_cnf(CNF.from_lists(2, [[1], [2]])),
                                  creation_precision=8,
                                  defining_polynomial=first_irreducible(2))
modes = make_geometry_point_modes(source, node=2, precision=8,
                                  extension_degree=2, zeta=(1, 0))
beta = (0, 0, 1, 1, 0, 0)
zero = certify_geometry_point_matching_zero(modes, beta)
assert zero['status'] == 'FINITE_STRUCTURAL_ZERO_CERTIFIED'
assert replay_geometry_point_matching_zero(modes, zero['certificate'])['valid']
assert direct_geometry_tuple_contribution(parent, modes, beta)['result'] == ((0, 0),)
result = contract_geometry_point_expansion(parent, modes, max_work=1_000_000, timeout_s=20)
assert result['direct_oracle_matches'] and result['result'] == ((64, 0),)
pruned = contract_geometry_point_expansion(parent, modes, max_work=1_000_000,
                                            timeout_s=20, enable_hall_pruning=True)
assert pruned['result'] == result['result'] and pruned['hall_pruned_tuples'] >= 1
row = next(row for row in pruned['tuples'] if row['beta'] == beta)
assert row['structurally_zero'] and not row['children']
```

One run of this exact fixture visited 23 tuples and skipped one after Hall
verification. The reported algorithm counters were 1,910 work units
without pruning and 2,377 with pruning, including 544 matching/witness
units; the separate direct oracle used 48 units. On this fixture, matching
cost more in the measured unit model than the child work it saved. These
units are not complete arithmetic-bit, memory, or wall-clock measurements.

Use `PYTHONPATH=src` when running outside an installed project. Source
geometry validation, mode replay, hashing, and matching setup are not all
charged to one global work or memory budget. The APIs expose finite checks;
they do not certify the deterministic labeling or theorem-scale recurrence.
Hall pruning is opt-in; it independently checks each matching witness before
skipping its children, charges matching and witness steps to the bounded
point-expansion work counter, and still runs the direct oracle. The report
does not claim that the extra matching work makes the full calculation faster.

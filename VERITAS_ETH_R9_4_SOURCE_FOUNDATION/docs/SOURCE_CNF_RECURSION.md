# Source-shaped CNF reduction and checked finite recursion

This adds an executable bridge from `subsec:sharp-fixed-density` of the pinned
preprint to the existing bounded `tapered_v4` research recursion. It does not
implement the manuscript's active theorem schedule or establish its runtime.

`source_cnf_network` removes tautological clauses, deduplicates literals,
constructs a trivalent equality tree for each occurring variable, and subdivides
every edge with a binary equality factor to obtain a bipartite network. An
empty clause remains a zero scalar. Declared variables no longer occurring
contribute a separate factor of two each. The number of model assignments is
preserved because equality fixes a unique assignment on every auxiliary wire.
`source_cnf_check` separately reconstructs normalized clauses from the input
and checks clause tables, variable ownership, tree connectivity and degrees,
and subdivision equality factors. The checker verifies a finite graph; it is
not a machine-checked proof for all inputs.

`count_source_cnf_finite` checks this graph, encodes entries at precision
`n+1`, invokes the existing finite recursion, and multiplies the completed
scalar residue by `2**unused` before exact count recovery. Set
`verify_exhaustive=True` to also compare the count against a separate bounded
assignment enumerator; its variable and estimated-work caps are checked
before execution. The oracle and graph checker are separate from the
recursor's cooperative elapsed-time budget and are not hard OS limits.

```python
from veritas.core.cnf import CNF
from veritas.research.tapered_v4 import RecursionPolicy, count_source_cnf_finite

formula = CNF.from_lists(1, [[1]])
policy = RecursionPolicy(leaf_edge_limit=1, allow_nonshrinking_leaf=True,
                         verify_point_identities=True)
result = count_source_cnf_finite(formula, policy, extension_degree=3,
                                 verify_exhaustive=True)
assert result['status'] == 'EXACT_COUNT_FINITE' and result['count'] == 1
```

Active calls of at most two wires automatically compare each complete child sum
against a direct half-edge sum. `verify_point_identities=True` requests that
check for every active call within the configured oracle cap, using the shared
work and time budget. The two calculations use different contraction formulas,
but share exact ring operations, parent entries, packet data and Cauchy shifts;
it is therefore an independent *contraction* check, not a fully independent
implementation of every mathematical component. It is limited to at most four
parent edges and fails closed above the configured cap. Results and oracle work
are recorded in the finite transcript and ledger.

The example enables a **finite nonshrinking-child fallback**, recorded in its
transcript. Turning it off returns `INCONCLUSIVE_NONSHRINKING_CHILD` for this
example. The direct assignment leaf is used only according to the explicit
finite policy. `mode='theorem'` remains disabled and returns
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`. The arithmetic, packing, weighted
modes, child identity, interpolation and memory complexity have not been proved
for all theorem inputs. The current explicit graph, mode, precision, tuple and
extension-degree caps exclude the active theorem regime. No subexponential
runtime, polynomial-space qualification, or formal verification is claimed.

Reproduce from the snapshot root:

```sh
PYTHONPATH=src python -m pytest -o addopts= -q tests/test_source_cnf_recursion.py
```

There is a concrete incompatibility between the current explicit 64-wire graph
cap and any active call satisfying the paper's packing inequalities. An active
call requires `u >= 1`, so `a >= 2`, `L >= 4`, and `D_arr >= 64**4 = 2**24`.
Since `Delta >= 2L >= 8`, the hypothesis `M >= 2 D_arr**2 Delta` implies
`M >= 2**52`. `inspect_active_theorem_capacity` reports this necessary bound;
reaching it does not establish that the other hypotheses hold. Supporting the
active theorem branch therefore requires a different, compact representation
and construction path, as well as the still-open correctness and cost proofs.

For optional per-tuple checking, set `verify_tuple_identities=True`; the direct
half-wire/row-selection oracle checks every emitted tuple at active nodes with
at most three parent wires. The finite recursor now checks each constructed
packet recipe and actual group loads and uses the full-node source Hermite
formula. See [mathematical repair progress](MATHEMATICAL_REPAIR_PROGRESS.md) for
the exact coverage and remaining proof obligations.

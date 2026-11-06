# R9.7 finite execution, distribution and accounting

## Explicit overflow policy

The default finite boundary algorithm still refuses unsupported work. A new
policy permits deterministic certified factor elimination when the *immediate*
boundary child-call lower bound would exceed the remaining call budget:

```python
from veritas.research.finite_reductions import BoundaryPolicy, contract_boundary
policy = BoundaryPolicy(on_call_overflow="certified_elimination")
answer = contract_boundary(network, precision=17, policy=policy)
```

For the two dense all-one factors sharing 16 wires, strict mode now refuses after
one visit, before attempting 131,072 children. Opt-in elimination computes 65,536.
The algorithm and triggering counts appear in the certificate. It does not catch
an invalid proof or an arithmetic failure and turn it into a different answer.
The route is unavailable with `piece_method="tapered"`.

Production elimination and an independently implemented bit-gather checker each
compute every intermediate table. The checker validates its exact table hash,
scope and eliminated edge, then its scalar result. The same checker can consume
a saved boundary certificate. All occurrence indices are preserved.

The strict format remains `VERITAS_FINITE_BOUNDARY_V1`; opt-in routing uses
`VERITAS_FINITE_BOUNDARY_ELIMINATION_V2`. Strict certificates omit the new default
field for historical schema compatibility. A historical certificate also binds
its original source bytes; compatibility does not waive source mismatch.

Caps remain: 16 explicit network wires, at most eight direct leaf wires,
100,000 configurable boundary calls (12,000 default), 100 million configurable
work units (15 million default), 240 seconds configurable (120 default), and
64 MB configurable certificate size (8 MB default). Elimination tables are capped
at 65,536 entries. Admission adds factor/table/precision limits. Work and deadlines
are cooperative. Exhaustion returns an inconclusive status with no accepted count.
The opt-in route broadens tested finite support; it does not promise that every
legal 16-wire instance fits every policy budget.

CLI example:

```sh
python -m veritas.research.finite_reductions input.cnf \
  --on-call-overflow certified_elimination --write count.json
python -m veritas.research.finite_reductions input.cnf \
  --on-call-overflow certified_elimination --replay count.json
```

## Standalone installation and content identity

The public package version is **3.8.2.post97**: engine base 3.8.2 plus research
checkpoint 97. Import metadata and API metadata use that same version. R9.7 remains
a finite research release.

`seal_wheel_sources.py` copies the immutable paper assets and pin configuration,
then records the checkout source digest for wheel assembly. An installed package
reconstructs the same sorted virtual-path manifest from its actual Python files,
paper files, packaged pyproject and conformance document. Added/deleted/changed
audited files and symlinks invalidate the binding. Checkout and installed-wheel
certificates have the same content identity.

Paths use POSIX separators and UTF-8; the digest hashes a canonical sorted JSON
mapping of paths to SHA-256 content hashes. Generated evidence, compiler binaries,
Python caches, tests, scripts and release manifests are excluded from this runtime
digest. The complete release manifest covers scripts, tests and proof sources.
Proof evidence additionally binds its own proof-source inventory. The bundled
source pin is excluded from its own hash. A hash match is unsigned integrity
evidence; it does not authenticate who built or ran the program.

Rebuild after changing package source:

```sh
python scripts/seal_wheel_sources.py
python -m pip wheel --no-deps --no-build-isolation -w ../wheelhouse .
python -m pytest -q tests/test_r96_wheel.py
docker build -t veritas-eth:r97 .
```

The wheel regression installs outside the checkout, evaluates a signed one-wire
network, replays a checkout certificate, rejects an extra installed source file,
evaluates a source leaf and rejects a changed manuscript. Docker uses installed
package resources from `/tmp`; its local verification is separate from hosted CI.

## Measurements and limits

`validate_r97_matrix.py` runs each of 15 cases in its own subprocess. Families at
12, 14 and 16 wires include satisfiable/conflicting CNFs, signed cycles,
disconnected networks and the dense two-factor obstruction. Each result is checked
against direct enumeration, conventional elimination and an independent proof-tree
consumer. CNF cases additionally use conventional DPLL. Both strict refusals are
recorded before opt-in elimination. Wires are tensor edges/literal occurrences,
not the number of SAT variables.

Wall time, process CPU time and per-case process-lifetime peak RSS are separate
fields. They include setup and checking where the field says so. Local timing is
single-machine evidence and may include other validation load. The matrix records
slower cases: plain factor elimination is much faster than boundary recursion on
the weighted cycle. No practical SAT speedup is qualified.

The ordinary boundary recurrence includes a full sum over `2^|B|` assignments and
both child calls per assignment. The elimination path has work proportional to
the actual intermediate table sizes times bucket membership. No polynomial-space
or subexponential bound follows from either recurrence.

`reference_multiply_operand_bit_products` is an observed operand-width product
sum in the elimination checker only. It excludes modular reduction, indexing,
hashing, serialization, allocation and unrelated arithmetic. It is a separate
counter, not included again in aggregate work units and not actual CPU bit work.
The complete bit-cost field remains false; actual machine bit operations are
unknown. Process RSS is measured, and a hard memory limit is enforced only in the
explicitly constrained Docker verification. General memory/bit-complexity proof
status is `COMPLEXITY_NOT_ESTABLISHED`.

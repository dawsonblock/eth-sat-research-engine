# Finite general packet support and shrinking recursion

This development extends the bounded R9.9 packet engine. The source schedule,
`contract_source` refusal boundary and old complete weighted tuple executor
remain separate. No source qualification, universal Python refinement,
bit-time bound or polynomial-space theorem follows from these experiments.

## Exact support calculation

For a packet, write its row factors as

`A_y(X,Y) + (2Y_y-1) sum_m c_ym Z_m`.

The complete geometric basis is constructed and independently checked first.
Two modes may be identified only if they have exactly the same packet,
source group, target group and source linear form `L_m(X)`. Replacing their
coefficients by their sum is the distributive law after substituting that
identical linear form. All coefficient sums are reduced at the prescribed
point precision. The common weight is the minimum original weight, which
retains the required divisibility for the sum. Cancellation may remove an
identically zero coefficient vector.

The resulting product is affine in the modes separately in each row factor.
An exponent vector can occur only if its mode occurrences can be assigned
injectively to eligible row factors. A mode shared by two rows may therefore
have exponent two. The producer multiplies Boolean supports; the checker
enumerates exponent multisets and independently solves this assignment problem.
Both preserve the weighted cutoff. Any support or verification budget overflow
refuses the entire point before returning a result.

Terms outside this support have zero formal target coefficient. Terms beyond
the weighted cutoff are zero modulo the point modulus. The sum over the
supported folded basis thus equals the original retained weighted sum, but
it does **not** enumerate the original stream. Reports explicitly distinguish
the original weighted count, folded weighted count and evaluated support.

For every supported tuple the executor constructs all 64 actual group children,
checks their independent port and immutable recipe descriptions, and contracts
each child. It does not skip a child because an earlier factor was zero.

## Full parent recovery

`recover_supported_parent` uses the complete `M(2L-1)+1` residue-distinct grid
at every required source-shaped Hermite node. It retains the existing exact
rational tapered recovery. Its independent consumer reconstructs every child,
recomputes every leaf value and checks every point against independent
half-edge Cauchy elimination before replaying recovery. This bounded entry
point requires all generated children to have at most four edges. It reports
shrink separately; small equality fixtures do not satisfy the source shrink
factor.

`contract_packet_recursion` also accepts `point_strategy='certified_support'`
and an explicit `max_points` limit. The default remains `complete_weighted`.
The larger grid option alone does not make a two-level run fit the budgets.

## Degree-certified shrinking path

`contract_supported_recursion` is a separately named finite optimization.
Every nonleaf transition enforces `64 M_child <= 6 M_parent` for all children
before any recursive call. Successful leaves have at most four edges. A
depth, precision, tuple, work, time, call or evidence limit returns inconclusive
without a result.

For a row tensor constant on all its Boolean inputs, its canonical
creation-time value factors out. Summing a row port's two affine factors gives
one exactly. Therefore only the ports of nonconstant row tensors contribute
deformation degree. If there are `k` such ports, `d=k(2L-1)` is a valid degree
bound. The same cancellation proves that supported tuple occurrences need
only be assigned to these ports. This is a statement about the contracted
coefficient, not about every unsummed packet entry being zero.

Row constancy is checked from original immutable recipes at their creation
precisions by production and independent arithmetic. The certificate binds
the full parent and contains no network contraction value. Canonical lifting
is never treated as a ring homomorphism.

This path uses `d+1` residue-distinct points at **each** prescribed node, with
the original point precision. It interpolates the entire degree-bounded
polynomial `F(t+alpha z)` and evaluates it at `z=-t/alpha`. The denominator
loss is at most `(a+1)d` bits, checked before evaluation. All nodes must recover
the same parent residue. Coefficients above `d` are exactly zero. This recovery
is explicitly recorded as `DEGREE_CERTIFIED_TAYLOR_AT_EACH_SOURCE_NODE`; it
does not claim to execute the manuscript's tapered functional.

Evidence may be streamed through an output callback. The production engine
retains its active grids and point construction state, rather than the whole
recursion transcript. Total evidence bytes are still capped. This design is
not a proof of polynomial peak space.

## Remaining work

The literal source-active executor, source-compliant padded packing, general
jet-valued input interface, arbitrary-depth executable refinement, and full
bit-time/space analysis remain open. Nonconstant rows without a useful degree
or support reduction can still exceed these finite budgets. These refusals
are expected and do not authorize incomplete tuples or oracle substitution.

## External commands

From this development checkout, choose a new evidence directory outside it:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r99.cli \
  examples/r99_multislot_crossing2.json \
  --layout-file examples/r99_multislot_crossing2_layout.json \
  --output /absolute/external/evidence/crossing-report.json \
  --certificate /absolute/external/evidence/crossing-certificate.json \
  --max-work 1000000000 --max-seconds 600 --max-certificate-bytes 100000000
```

Replay uses the same input, layout and certificate, adds `--verify`, and uses
a new output report path. The supplied small fixture exercises crossing modes,
shared modes with exponent two, nonconstant tensors and both node valuations.

The larger recursive fixture uses the following separate driver:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r99.cli \
  examples/r99_nonconstant_matching242.json --mode recursion \
  --layout-file examples/r99_nonconstant_matching242_layout.json \
  --output /absolute/external/evidence/recursive-report.json \
  --certificate /absolute/external/evidence/recursive.events \
  --max-work 1000000000 --max-seconds 3600 --max-calls 2000000 \
  --max-certificate-bytes 100000000
```

To replay the recursion, use the same arguments with `--verify`, add
`--result-report /absolute/external/evidence/recursive-report.json`, and select
a different `--output`. Replay independently reconstructs all actual child
recipes, re-evaluates the leaves and recovers each parent by direct Lagrange
evaluation with denominator accounting. It rejects missing or duplicate
events and recomputes the actual call, point, tuple and depth ledger.

An inconclusive recursive run may leave a partial event file. It has no
successful result report and cannot pass complete replay. Existing files are
preserved rather than overwritten.

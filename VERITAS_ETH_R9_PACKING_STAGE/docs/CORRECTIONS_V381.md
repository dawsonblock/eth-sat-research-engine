# v3.8.1 correction scope and source-pinned obligations

The base is the supplied `VERITAS_ETH_v3.8.0_FULL_UPGRADED.zip`, SHA-256
`2d07ab851a8af4fc13d3d674bd60407de80fd38dbbfc06a8d4745ecca16f7f72`.
This is a local engineering candidate, not an independently qualified release.

## Corrections

* v3.8 construction and replay use one shared cooperative deadline and work
  ledger across validation, elimination, direct oracle and optional v3.7
  comparison. The v3.8 API shares the same ledger for its setup, construction
  and verification. Certificates record deterministic charged-event phase
  totals. Replays also charge their own input/finalization phases against the
  same limit, although those replay-only events are not in the source
  certificate. This changes the v3.8 certificate schema to
  `VERITAS_EXACT_FINITE_D44_CHILD_ELIMINATION_V381`; old v3.8 certificates are
  rejected instead of being silently relabeled. The v3.7 standalone verifier
  and original replay semantics remain intact.
* The work counter measures checkpoints, selected table/assignment events and
  v3.8 jet-ring calls; it does not count all operations in validation, v3.7
  comparison, multiplication internals, integer bit complexity, JSON parsing,
  serialization after return, or peak memory. Checks run at cooperative
  boundaries: a slow operation can exceed the deadline before the next check.
  A returned certificate is checked after the last potentially expensive
  construction stage. This is **not** a hard OS-enforced timeout or memory
  limit. Hostile/multi-user deployments need process isolation and OS quotas.
* Oracle `ImplicitBudgetExceeded` and other budget exceptions now yield
  `INCONCLUSIVE_RESOURCE_LIMIT` in v3.8 certificate verification. Invalid
  certificates continue to fail closed. v3.8 accepts `max_work` 100–2,000,000
  and `timeout_s` in (0,30], checked before mode validation.
* Original factor caches now include the full immutable factor label, ordered
  ports and entries. Different factors may share a label without collision.
* Manifest verification uses explicit checks rather than `assert`, including
  under `python -O`; it rejects changed, missing, extra, duplicate and escaping
  files. The builder regenerates both manifests and explicitly verifies its
  source tree and ZIP. These files are checksums, **not signatures**.
* The `test` extra includes NetworkX; the included CI configuration now lists
  Python 3.10 and 3.12. A configuration change is not evidence of a hosted run.

## Independent finite dense experiment

`src/veritas/research/dense_cauchy_testbed.py` implements a separate scalar
experiment with two full-scope Boolean tables and 8, 10, 12, 14, or 16 wires.
It constructs the L=2 Cauchy polynomial kernel independently from its product
formula at T=4. At this point its matrix is the identity modulo two; expanding
each row factor as equality plus twice a perturbation yields subset modes.
It sums only weights below P modulo `2**P`, compares them with a packet-matrix
contraction, and (by default) checks an independent direct half-edge sum at
8 wires. The half-edge oracle refuses 16 wires under its `2**16` pair cap.

This is deliberately **not** the manuscript's D.4.4 tile-mode construction:
T=4 is used for a finite polynomial identity, outside the manuscript's
L=2 interpolation node set; it is not reconstruction at zero. Retained terms
still contain the original full-scope tensors, so their largest child scope is
M, not M/8. The two tensor tables are generated from fixed seeds and the script
records their SHA-256 digests. Scalar operation counters include only dot
products and packet transforms, excluding mode/kernel construction, modulo
cost, the independent oracle and integer bit costs. The table count is not a
peak-byte measurement. No full operation, memory, runtime or asymptotic bound
is claimed.

Run `PYTHONPATH=src python scripts/validate_dense_v381.py`. Precision defaults
to 2; higher mode counts can hit the explicit operation cap. The original
v3.8 fixed-beta child engine still supports at most six wires. This scalar
testbed does not extend that engine or provide an end-to-end recursive solver.

## Pinned manuscript comparison

Source: OpenAI math repository commit
[`4eaee87548250b2682affda7d05d947c05554bae`](https://github.com/openai/math/tree/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build).
`main_full_version.tex` SHA-256
`b2e6159d4fb7ea6aa4f89ac15605152b0333a5f7cafe93323492bc20a5c066aa`;
its included `quantitative-contraction.tex` SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
Pinning identifies the source and does not verify its proof.

| Manuscript obligation | State here |
| --- | --- |
| D.3 packet construction and numerical preconditions | Finite checked certificates; theorem preconditions are generally not met by small examples. |
| D.4.4 geometric tiles and valuation-weighted mode tuples | Finite six-wire reference with source replay and direct half-edge comparison. The 8–16-wire scalar experiment uses a different subset expansion. |
| Fixed-beta packet tensors and group-local children | Finite exact reference and bounded elimination; no recursive regeneration. |
| `r=64`, `6M/r < M/8`, and degree bound at every depth | **NOT IMPLEMENTED / NOT PROVEN** in this finite engine. |
| Depth-dependent precision, interpolation, and bit/space recurrence | **NOT IMPLEMENTED / NOT PROVEN** end to end. |

Neither the 8–16-wire identity checks nor the package tests establish a
general subexponential contraction, an ETH result, or production readiness.

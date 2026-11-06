# VERITAS-ETH v3.8.0 — validation and scope report

## Source provenance

Source base: `VERITAS_ETH_v3.7.0_D44_CHILD_REFERENCE_FULL_SOURCE.zip`, present in the same conversation's runtime. The entire cumulative codebase was extracted and copied forward; v3.8 is not a replacement stub.

## Delivered

- `src/veritas/research/eth_child_elimination_v38/`: exact finite factor-table contraction of group-local fixed-beta D.4.4 children with exact extension-ring jets.
- Contraction planner using a min-neighbor ordering, component decomposition, and small packet factor cache shared between mode tuples.
- Resource guards for work, time, intermediate factor sizes, and cache size.
- Independent direct-halfedge comparison on each constructed certificate; optional exhaustive v3.7 cross-check.
- Source-replayed certificate checker with explicit unproven-theorem scope flags.
- CLI `veritas-eth38` and FastAPI `/v1/research/eth/finite-child-elimination` construct/check/status endpoints, with a local browser demo.

## Execution evidence

- Full inherited plus new test collection: **488 tests**, `PYTHONPATH=src pytest -q --disable-warnings`, successful exit status 0.
- 40 new seeded finite exact comparisons: `PYTHONPATH=src python scripts/validate_child_elimination_v38.py` — passed.
- 40 inherited v3.7 direct-reference comparisons: `PYTHONPATH=src python scripts/validate_d44_child_v37.py` — passed.
- New targeted tests, including certificate tamper detection and resource failure cases, passed.
- CLI construct/check round-trip with optional v3.7 cross-check — passed.
- FastAPI status, construct, certificate-check round-trip with TestClient — HTTP 200 and independently verified result.
- See `SHA256SUMS.txt` for per-file integrity and the extracted-archive smoke checks for packaging validation.

Example (2-variable one-clause finite test): extension-jet result `[[0,0,0],[16,0,0]]`, maximum factor entries 4, bounded factor evaluator work 70 (not a comparable runtime metric across versions). These are residue coefficients, not an ordinary integer solution count.

## Mathematical limitations

The work here replaces **exhaustive contraction of fixed-beta group-local children** with bounded exact bucket elimination. It does NOT recursively apply the manuscript's Cauchy/packing child construction to the smaller children, does not implement the required depth-dependent precision and lift schedule, and does not prove a universal `M/8` child bound, polynomial-space bound or subexponential runtime. The current generator retains its small-size reference limitations. No general speedup has been established by benchmarks.

## Next blocking milestone

Construct creation-time immutable implicit child network descriptions, implement recursive regrouping and mode expansion at descendant levels with appropriate precision increases, and independently validate child size, degree, and runtime/space recurrences against a source-pinned statement of D.4.4. Do not merge this with production exact SAT until proof and performance gates pass.

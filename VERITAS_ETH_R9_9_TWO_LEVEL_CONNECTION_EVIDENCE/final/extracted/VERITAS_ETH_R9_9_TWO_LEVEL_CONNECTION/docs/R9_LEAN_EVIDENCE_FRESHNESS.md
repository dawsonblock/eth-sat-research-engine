# Lean evidence freshness boundary

## Defect repaired

The R9.1 release aggregator previously accepted a stored Lean report whenever
its top-level `status` field was `PASS`. It did not compare the report's
per-module source hashes with the current checkout. An edit or deletion of a
Lean proof could therefore leave an obsolete positive result visible in the
aggregate report.

## Current checks

The Lean gate now records a canonical proof-source manifest digest and the
digest of `scripts/validate_conditional_expectation_lean.py`. Before using
that report, `scripts/validate_r91.py` checks:

* the manuscript bytes still match the pinned digest and path;
* the current `lean-toolchain` equals the report, and its recorded Lean
  version output matches the pinned version;
* the exact ordered proof-module inventory matches the current gate contract;
* every proof module exists as a regular non-symlink file and its current
  bytes match the recorded SHA-256 and proof-manifest digest;
* every recorded module returned zero and has `sorryAx_absent: true`;
* each central theorem report is present and its audited axiom set passed;
* the theorem-mode field remains explicitly false.

Any mismatch produces `STALE_OR_MISMATCH` for the Lean aggregate gate. The
release report then clears every formal qualification derived from that
evidence. Mathematical claims are mapped to their specific Lean-gate fields
or theorem reports rather than inferred from an overall pass alone.

## Trust limit

These SHA-256 values detect stale or accidentally mismatched local evidence;
they do not authenticate who produced the JSON, attest to a Lean binary, or
provide a cryptographic signature. The Lean executable and the validator
remain trusted computing-base inputs. A fresh hash match is therefore
reported as `PASS_HASH_MATCH_UNAUTHENTICATED`, not as signed or independently
reproduced proof provenance. It also says nothing about Python/C++ source
refinement or the unimplemented recursion theorem.

## Negative coverage

`tests/test_r91_fresh_lean_evidence.py` exercises changed and deleted proof
files, missing/duplicated/reordered module records, manuscript and toolchain
changes, validator-source changes, incomplete axiom audits, and absent
manifest fields. Each case invalidates the old report and clears formal claim
flags. These are checker tests, not additional Lean proofs.

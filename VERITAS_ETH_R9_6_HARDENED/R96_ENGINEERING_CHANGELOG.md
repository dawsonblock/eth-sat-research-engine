# R9.6 engineering changelog

Every entry states the defect, the reproduction, and the repair.  "Reproduced"
means the failure was observed in this session on a disposable copy of the R9.5
release, not inferred from a bundled log.

Baseline for all comparisons: `VERITAS_ETH_R9_5_RECIPE_EXECUTION_PARTIAL_FULL_UPGRADED.zip`,
SHA-256 `5d5b88c748414bb468dc063de59fe94974beede4934c2500346fc0da4ece3756`,
821 members, 820 manifest entries.  Baseline suite on macOS/arm64, CPython
3.12.0: **1343 passed, 32 skipped, 0 failed**.

---

## New files

### `scripts/release_integrity.py` (new, 243 lines)

Immutable release-input verification.  Three artifacts, deliberately not
merged: the release-input manifest (read only), a runtime-evidence manifest for
freshly generated files, and an integrity snapshot used to prove nothing
changed during a job.  Subcommands `verify`, `snapshot`, `compare`, `evidence`.
Exit codes 0/1/2.  `--root` defaults to the repository root.

### `scripts/_evidence.py` (new, 77 lines)

Resolves where a validator writes freshly generated evidence:
`--output PATH` → `VERITAS_EVIDENCE_DIR` → the historical in-tree default.
Raises `EvidencePathError` for a malformed `--output` so the caller fails
closed.

### `scripts/validate_r96_hardening.py` (new, 247 lines)

Runs eight checks and emits `VERITAS_R96_HARDENING_QUALIFICATION_V1`.  A check
that cannot run is `NOT_RUN` with a blocker; it is never promoted to `PASS`.

### `scripts/benchmark_r96.py` (new, 248 lines)

Packet-coefficient timings (R9.6 first-order/sparse DP vs the naive Cartesian
reference) and a #SAT scaling series with brute-force ground truth.  Records
wall, CPU, peak RSS, work units, nodes and refusals.  States explicitly that
work-unit definitions differ and that no asymptotic claim follows.

### `src/veritas/research/tapered_v4/manuscript.py` (new, 165 lines)

Content-addressed access to the pinned manuscript through
`importlib.resources`, with exactly two permitted sources and a hash check on
every read.

### `src/veritas/research/tapered_v4/_resources/quantitative-contraction.tex` (new)

Byte-identical copy of `paper/quantitative-contraction.tex`
(`671642d7…873860`), shipped in the wheel via `[tool.setuptools.package-data]`.

### `src/veritas/research/tapered_v4/coefficient_budget.py` (new, 115 lines)

`CoefficientAdmission`: one atomic, shape-aware counter for every stored
coefficient class.

### `src/veritas/research/tapered_v4/packet_coefficients.py` (new, 220 lines)

`first_order`, `sparse_dp`, `unpruned_reference`, `row_factors`,
`target_coefficient`, `algorithm_for`.  Documents why pruning by exact ring
zero is sound and pruning by individual modular coordinate is not.

### `src/veritas/research/tapered_v4/canonical.py` (new, 104 lines)

Canonical ASCII JSON and domain-separated, versioned SHA-256 digests with an
explicit `does_not_prove` list.

### `src/veritas/research/tapered_v4/validators.py` (new, 408 lines)

Total, fail-closed validators for entry, leaf, certificate and replay
documents.  Pre-decode bounds on bytes, depth, node count and integer
magnitude.

### `src/veritas/research/tapered_v4/parent_child.py` (new, 453 lines)

`VERITAS_PARENT_CHILD_CERTIFICATE_V1` producer and independent consumer for one
recursion level.

### `src/veritas/research/tapered_v4/source_regime.py` (new, 209 lines)

The executable unreachability derivation, the two separated regime labels, and
`SymbolicSourceSize`.

### `adversarial/check_r96_independently.py` (new, 173 lines)

Independent checker that shares no arithmetic with the package: it expands
`(1-z)^n` with its own integer polynomial code and recomputes the delivered
evidence.

### Tests (new, 8 modules, 217 test cases)

`test_r96_release_integrity.py`, `test_r96_manuscript_resource.py`,
`test_r96_coefficient_budget.py`, `test_r96_packet_coefficients.py`,
`test_r96_serialization.py`, `test_r96_parent_child.py`,
`test_r96_source_regime.py`, `test_r96_hermite_audit.py`.

### Docs (new)

`docs/R96_EXACT_RING_CONTRACT.md`, `docs/R96_HARDENING.md`.

---

## Modified files

### `.github/workflows/test.yml`

**Defect (reproduced).** The `test` job ran `python scripts/validate_v08.py`
before `python scripts/verify_manifest.py`.  `validate_v08.py` rewrote
`validation/validation_v08.json`, which is a manifest entry, so an untouched
release failed its own manifest check:

```
PASS: 820 complete file hashes match release manifest; no unlisted files
(validate_v08.py runs)
FAIL: checksum mismatch: validation/validation_v08.json
```

**Repair.** All four jobs now (1) run `release_integrity.py verify` and
`snapshot` immediately after checkout and before `pip install`, (2) set
`VERITAS_EVIDENCE_DIR` outside the workspace and pass explicit `--output`
destinations, and (3) run `release_integrity.py compare` at the end with
`if: always()`, failing the job if any release input changed.  The `test` job
also runs `python -O scripts/release_integrity.py verify`.  A new step runs
`validate_r96_hardening.py`.  No manifest entry was removed and no historical
timing value was rewritten.

### `scripts/verify_manifest.py`

`IGNORED_DIRS` extended to the same cache set `build_release.py` already
ignored (`.hypothesis`, `.nox`, `.cache`, `node_modules`, `dist`).  Without
this, a Hypothesis cache created by a test run would be reported as an
unlisted release file while `build_release.py` would not list it — the two
would disagree permanently.  No release-input path was added to the ignore set.

### 21 writing validators

`validate_v08/v09/v10/v11/v12/v13/v17/v21/v24/v36/10000`,
`validate_r91`, `validate_r91_cpp`, `validate_r91_python_model`,
`validate_r93_packet_model`, `validate_r94_foundation`, `validate_r95_recipes`,
`validate_r9_streaming_packing`, `validate_conditional_expectation_lean`,
`benchmark_r91_cpp`, `benchmark_r91_scorer`.

Each now resolves its destination through `_evidence.evidence_path` or an
`--output` default derived from `VERITAS_EVIDENCE_DIR`.  Behaviour without the
variable is unchanged, so local regeneration still reproduces the documented
paths.

### `src/veritas/research/tapered_v4/source_state.py`

**Defect (reproduced).** `inspect_source_node` read the manuscript from
`Path(__file__).resolve().parents[4] / "paper/quantitative-contraction.tex"`.
In an isolated virtual environment with only the wheel installed, the same
canonical call returned

```
{"status": "INCONCLUSIVE_SOURCE_MISMATCH", "reason": "pinned manuscript is absent or changed"}
```

**Repair.** `inspect_source_node(node, *, manuscript=None)` calls
`read_pinned_manuscript`.  The `pathlib.Path` import was removed; the module no
longer contains any parent-directory search.

### `src/veritas/research/tapered_v4/source_leaf.py`

`contract_source_leaf(..., manuscript=None)` forwards the explicit asset.  All
return paths now carry `schema: VERITAS_SOURCE_LEAF_RESULT_V1`; the theorem
refusal carries an empty ledger so a validator can treat it uniformly.

### `src/veritas/research/tapered_v4/source_recipes.py`

**Defect A (reproduced).** Four source-mode scalar coefficients were accepted
under `EntryLimits(max_coefficients=1)` and returned `((2, 0),)`, because only
creation-ring jets were counted.

**Defect B (reproduced).** `[z](1-z)^15` with a degree-2 extension and two jet
coordinates exhausted the 5,000,000-unit default budget after ~2.2 s with
`INCONCLUSIVE_RESOURCE_LIMIT`.

**Repair.** `compile_entry` routes every coefficient class through
`CoefficientAdmission` and admits dense tables and local matrices atomically
before validating any coordinate.  `evaluate_compiled` delegates to
`packet_coefficients` and records the chosen algorithm in the ledger.  The
`make_reference` structural pre-scan is derived from the admissible payload
size instead of `4 * max_coefficients`, which had rejected every realistic
payload under a small cap.

### `pyproject.toml`

`[tool.setuptools.package-data]` now ships
`research/tapered_v4/_resources/*.tex`.  No dependency was added or changed.

### `tests/test_lean_proof_gate_audit.py`

One assertion updated: it required the literal
`validation/r9_ci_proof.json` in the Lean job, i.e. it pinned the defect of
writing fresh proof evidence into the release tree.  It now requires
`"$VERITAS_EVIDENCE_DIR/r9_ci_proof.json"` **and** forbids
`--output validation/r9_ci_proof.json`.  The check is stricter, not weaker.

### `AGENTS.md`

A new R9.6 policy section at the top records the invariants above.

---

## Deliberately unchanged

* `paper/**` — byte-identical (verified by `diff -r`).
* `validation/**` — every historical evidence file is byte-identical to R9.5;
  no timing value was rewritten and no old evidence was re-signed.
* `proofs/**` and `lean-toolchain` — unchanged; the gate recompiled them.
* `cpp/**` — unchanged; rebuilt and differentially tested.
* `src/veritas/research/eth_*` — unchanged.
* `SHA256SUMS.txt` / `SHA256_MANIFEST.json` — regenerated as the final step for
  the *new* proposed release.  The R9.5 originals remain untouched in the
  original archive; both hashes are recorded in `R96_RELEASE_READINESS.md`.

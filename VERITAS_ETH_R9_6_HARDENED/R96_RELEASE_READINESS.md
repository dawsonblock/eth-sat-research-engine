# R9.6 release readiness

Three separate decisions, because they have three different evidence bases.
They must not be collapsed into one verdict.

| Decision | Verdict |
|---|---|
| A. Controlled bounded research use | **GO** |
| B. Installed-package deployment (library use) | **GO with the restrictions below** |
| C. Universal theorem-qualified execution | **NO-GO** |

---

## Gate results

| Gate | Verdict | Basis |
|---|---|---|
| **A** — bounded source execution hardened | **PASS** | CI release-hash integrity stable before and after validation; the wheel source path works; coefficient quotas enforced on every class; `[z](1-z)^15` returns `1` inside the default budget; arithmetic and refusal regressions pass; no new unexplained failures |
| **B** — finite parent/child verified | **PASS for the claimed finite domain only** | complete independent mode enumeration and `8/8` point-identity coverage on the certified two-wire, one-level fixture; immutable certificate; 12 adversarial mutations rejected |
| **C** — theorem-qualified implementation | **NOT MET** | source-active regime not implemented (and unreachable in this representation); no complete parent-to-children recursion; no Lean refinement map; no proved bit/time/space bounds |

**Gate C is not met, so theorem mode must fail closed — and it does.**  Every
emitted document carries `theorem_mode_enabled: false`, and
`source_active_status(..., mode="theorem")` returns
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

### Why Gate B is scoped the way it is

Gate B's own wording asks for "complete independent mode enumeration and
point-identity coverage **for the claimed test domain**".  The claimed domain is
one recursion level on a two-wire network with a degree-2 extension, precision
4, `a = u = 1`, radix 4.  On that domain the certificate is complete: every
required node and residue point appears, every admissible tuple is enumerated
in a deterministic order, every group child is rebuilt and recontracted by an
independent consumer, and the parent side is recomputed with the half-edge
oracle.

It does **not** cover:

* recursion below the first level (observed depth is one);
* the historical eight-wire transcript, which still reports
  `points_checked: 0 / 50`;
* the manuscript's `M/8` shrinking condition;
* any parameter regime outside the fixture.

Calling Gate B "PASS" without those four sentences would be a misstatement, so
they are part of the verdict.

---

## Decision A — controlled bounded research use: **GO**

Evidence:

* Release inputs verify before and after every job, with the same immutable
  bytes; no manifest entry was removed and no historical timing was re-signed.
* 1590 passed / 2 skipped / 0 failed on macOS/arm64 with the Lean toolchain and
  the native C++ build present; 1560 passed / 32 skipped / 0 failed without
  them.  Baseline was 1343 / 32 / 0.
* Lean 4.35.0 at the pinned commit recompiled 36 modules from source with
  axioms limited to `propext`, `Classical.choice`, `Quot.sound`.
* The C-ABI scorer rebuilt, self-tested, and passed the finite differential.

Conditions of use:

* Do not describe any result as a theorem, an ETH refutation, or a complexity
  bound.
* Do not present the certified fixture as evidence of recursion.
* Keep `INCONCLUSIVE_*` statuses intact in any downstream reporting.

## Decision B — installed-package deployment: **GO with restrictions**

Evidence:

* The wheel contains the pinned manuscript
  (`veritas/research/tapered_v4/_resources/quantitative-contraction.tex`,
  `671642d7…873860`) and is read through `importlib.resources`.
* An isolated virtual environment with no source checkout on `PYTHONPATH` and a
  working directory outside the repository returns the identical leaf result
  `((1, 0, 0, 0),)` for `SourceContext(2,1,1,1,1,1,19)` with zero edges.
* A missing, truncated or substituted manuscript refuses with
  `INCONCLUSIVE_SOURCE_MISMATCH` and yields no value.
* Read-only installation paths are supported (tested).

Restrictions:

* The package version stays **3.8.2**.  R9.6 is a research-revision label, not a
  package version bump; no upstream theorem statement or historical attestation
  was altered.
* The manuscript is content-addressed but **not publisher-authenticated**.  A
  hash match proves byte identity, not provenance.
* Only the bounded entry/leaf and finite-certificate APIs are supported for
  library use.  Theorem mode, the active source executor and any recursion API
  return `INCONCLUSIVE_*` by design.
* No service-level, concurrency or hard-memory guarantee is offered; budgets are
  cooperative and `hard_memory_limit_enforced` is `false`.

## Decision C — universal theorem-qualified execution: **NO-GO**

Blocking obligations, all open (see `R96_MATH_AND_PROOF_OBLIGATIONS.md`):

1. source-active executor and its schedule — **not implemented**; unreachable in
   the current representation (`lambda >= 131072` needed, `<= 1024` admissible);
2. universal mode-domain completeness;
3. parent-to-children identity at depth greater than one;
4. the manuscript's `M/8` shrinking bound;
5. universal Hermite functional and coefficientwise precision proof;
6. Lean → Python refinement map (`lean_python_builder_refinement_proven: false`);
7. proved termination and complete work/space accounting;
8. arbitrary-density count-preserving reduction and the #SAT theorem.

No amount of bounded testing closes any of these.

---

## Provenance and hashes

| Artifact | SHA-256 |
|---|---|
| R9.5 source archive (input, unchanged) | `5d5b88c748414bb468dc063de59fe94974beede4934c2500346fc0da4ece3756` |
| R9.5 `SHA256SUMS.txt` (input, unchanged) | recorded in `evidence/r95_original_manifest.sha256` |
| R9.6 source tree manifest | see `SHA256SUMS.txt` in the source archive (845 entries) |
| R9.6 source archive | see `SHA256SUMS.txt` of the evidence bundle |

Trust class for every hash here: **HASH_MATCH_UNSIGNED**.  These are local
hashes of a locally built tree.  They are **not** a publisher signature and
must not be presented as authenticated provenance.

## What was not run

| Item | Status |
|---|---|
| Linux x86-64 reproduction | **NOT_RUN** — no host in this session; the inherited R9.5 Linux result is not reproduced here |
| Windows reproduction | **NOT_RUN** |
| pybind11 module | **NOT_RUN** — built against a different interpreter ABI; the ctypes C ABI was used instead |
| Lean binary authentication | **NOT_RUN** — the toolchain was downloaded, not publisher-verified |
| Source-active execution | **NOT_IMPLEMENTED** |

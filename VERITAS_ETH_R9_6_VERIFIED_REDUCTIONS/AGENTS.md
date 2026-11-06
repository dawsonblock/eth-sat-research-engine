# R9.6 evidence and finite reductions
- Run the 38-module proof gate and both R96 validators. Boundary algebra, executable table restrictions, finite recipe point identities and manuscript-active calls have separate qualifications.
- Keep sealed manifests in the input tree and generate CI evidence in a disposable copy. Verify an installed wheel outside the checkout, preserving manuscript checks.
- The finite boundary experiment is defined on explicit integer tables. Preserve direct-parent checks as optional verification and reject incomplete constructions with no result.

# R9.5 entry-execution policy (supersedes source-foundation module counts)
- The gate has 36 Lean modules. Creation-coordinate lemmas are formal model results, not proofs of the Python recipe evaluator.
- `source_recipes` specifies exact entry semantics at creation precision; `source_leaf` executes only nodes with M <= H. Active source calls and theorem mode must remain refused.
- Dense recipe indices are lexicographic. The old described-network API uses little-endian port indices; the explicit bridge must preserve all assignments.
- Run the R95 validation, new recipe/leaf/grid tests, Lean contract faults, R94 differential and full suite. Keep paper bytes unchanged.

# R9.4 source-foundation policy (supersedes older module-count notes)
- The proof gate now has 34 modules. R94's candidate, keyed-run and finite-domain proofs are Lean model results; Python/C++ executable refinement stays false.
- `lean_model_full_run_correspondence_proven` may be true only with fresh R94 contract and keyed-run evidence. Do not describe the extensional dictionary model as verified CPython.
- Keep `SourceContext.size_parameter` distinct from node `edge_count`. Source admission is bounded structural validation and does not evaluate tensor recipe bytes or supply an active executor.
- Run `scripts/validate_r94_foundation.py`, the 34-module gate, new fault injections and the full suite. Never change theorem-mode refusal based on those results.

# R9.1 build and verification (applies to every version below)
- Build the C++ scorer with `cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release` and run `./build/cpp/veritas_d3_selftest` before any Python test that touches `score_backend`.
- `python scripts/benchmark_r91_scorer.py` writes `validation/r91_benchmarks.json`; it fails unless all three backends agree exactly. Never report a speedup without that flag.
- `python scripts/validate_r91.py` aggregates the gates. It must exit 0. `lean_model_candidate_score_identity_proven` is true (proved by `pyCandidateScore_eq`); `cpp_is_formally_verified`, `python_to_lean_source_refinement_proven`, and `cpp_to_lean_source_refinement_proven` must stay false, and `lean_model_full_run_correspondence_proven` stays false until the selection lemma is proved.
- The Lean gate now compiles 22 modules including `D3PythonScoreModel.lean` and `D3PacketBijection.lean`. Their central theorem names are namespace-qualified; keep the `#print axioms` lines and the gate list in sync.
- Do not describe the C++ backend as verified. Do not weaken `wordMatches_range_any` or replace it with a vacuous statement.

# Pinned-source policy (applies to every version below)
- The paper this project implements is vendored in `paper/` (OpenAI, *The Exponential Time Hypothesis is False*, 25 Oct 2026). Cite its labels (`app:tensor`, `lem:tensor-packets`, `lem:tapered-hermite`, `eq:tensor-parameters`, `eq:tensor-packing-conditions`, `subsec:tensor-children`), not "Appendix D". The "D.x" numbering is a legacy alias; the mapping is in `docs/OPENAI_PAPER_CONFORMANCE.md`.
- Any change to a schedule, packing, Hermite, mode, or count-recovery parameter must keep `tests/test_openai_paper_conformance.py` passing. If a paper formula changes, update the vendored source hash, the conformance doc, and the test together.
- Do not edit `paper/` in place. A new upstream revision is a new pinned directory plus an explicit diff note.
- `scripts/build_release.py` regenerates `SHA256SUMS.txt` and `SHA256_MANIFEST.json`; run it as the **last** step after all edits, and run `scripts/verify_manifest.py` afterwards. A stale manifest is a release-gate failure.
- `scripts/validate_tapered_v4.py` pins `max_work=3_000_000`; the eight-wire run charges about 2.13M units. Do not drop back to the 2M dataclass default.
- Packet sources come in two schemas (`VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1`, dense slots, and `VERITAS_ETH_D3_IMPLICIT_SPARSE_ACTIVE_V1`, occupied slots only). Every consumer must go through `real_packet_slots(packet, L)`, never `packet['slots']`.

# Shared-linear-summary policy (`eth_counting_v39`)
- This package implements `sec:counting` and `sec:construction` of the pinned preprint, not `app:tensor`. Do not merge its claims with the contraction reference; they are different halves and share no state.
- The counting identity is exact over `Q` and is verified against exhaustive enumeration. Keep `tests/test_counting_v39.py` and `scripts/validate_counting_v39.py` green on every change to the schedules, the swap matrix, the embedding, or the Taylor recovery.
- Never claim the paper's running-time bound from this package. `FormParameters.check()` and `CountingResult.layout['cost_hypotheses_hold']` report which numerical hypotheses fail, and at executable sizes most of them do.
- `M_0` must stay a sparse combination of permutations with support `|S| <= R-1` (`lem:swaps-support`). Do not replace the Walsh transform with a dense `D x D` matrix.
- Every new resource (copies, measurement rows, restriction pairs, work units) needs an explicit cap that fails closed.

# v3.8 engineering constraints
- Fixed-beta D.4.4 child contraction is exact over the extension jet ring but is **not** recursive application of the manuscript's child construction.
- Never claim universal M/8 size reduction, polynomial space, or subexponential time based on this finite implementation.
- Fail closed on time, arithmetic, table size, and work budgets; do not return partial values as counts.
- Preserve the v3.7 independent direct Cauchy oracle and its full source-replay certificates.
- Do not silently reduce or change the modular precision of an existing ring value.

# v3.6 developer constraints
- Do not claim M/8 shrinking child networks or subexponential complexity.
- Exact packet polynomial arithmetic uses Boolean idempotence X_i²=X_i, not ordinary formal power expansion.
- Verify against independently calculated Möbius coefficients and direct Cauchy half-edge oracle.
- Do not promote a new result on timeout or failed certification.
- Preserve original v3.5 regression and API behavior.

# v3.5 scope constraint
Never conflate finite mode-bond child index scopes with manuscript D.4.4 recursively generated child-network wire counts or claims of subexponential complexity.

v3.4.0: Structural D.3 port/mode ledger + checked v3.3 finite contraction bridge. See RELEASE_NOTES_V34.md. No M/8 child wire or ETH theorem proof.

# VERITAS-ETH v3.3.0 — finite recursive mode-bond contraction

New: exact recursive separator-style mode-exponent contraction, sparse conditioning, disconnected-component decomposition, deterministic memoization, triple-oracle source replay, CLI/API/browser integration and budgeted execution. See `docs/FINITE_RECURSIVE_MODE_BONDS_V33.md` and `RELEASE_REPORT_V33.md`. **Not** the manuscript D.4.4 recursively shrinking packet tensor algorithm or an ETH result.

```bash
python -m pip install -e ".[test]"
veritas-eth33 construct --n 2 --clauses-json "[[1,2]]" --output cert.json
veritas-eth33 check --certificate cert.json
python scripts/validate_v33.py
```

---

# v3.2 engineering constraints

Before changing the mode bond system, preserve the exact v3.1 geometric-mode source and the independent 4**M half-edge oracle. Never label finite mode-exponent child tensors as the manuscript’s recursively shrinking packet tensors; never claim M/8 or subexponential complexity without implementing and proving the specified construction. New certificates must reject invalid scope claims, preserve exact 2-adic extension jet arithmetic and fail closed on resource caps. Always run `tests/test_v32_mode_bonds.py` and `scripts/validate_v32.py` before release.

---

## v3.0 release policy

Keep the finite implicit boundary-child factorization separate from the **unimplemented** D.4.4 geometric-tile mode-selected recursive child theorem. No subexponential claim. Independently verify D.3 certificates, direct Cauchy half-edge jets, and `W(0)=I` exact count. Refuse partial results on budget exhaustion. Keep old modes/certificates stable. Each upgrade requires test and ZIP-manifest validation.

## v2.9 release policy

Keep exact finite rank-one extension-ring modes and the manuscript's geometric-tile D.4.4 algorithm distinct. Never claim the finite rational Hermite reference has the manuscript's asymptotic complexity. All node precisions and reported mode weights require independent mathematical checks. Preserve the v2.8 code and all inherited tests. No incomplete results presented as exact. Run v2.9 validation and integrity scripts before release.

## v2.8 release integrity and mathematical scope

Read `docs/SOURCE_REVISION_DIFFERENCES_V28.md` before touching Appendix D parameters. Do not restore ceiling without an immutable manuscript source and documented rationale. Never invert an even denominator in finite 2-adic arithmetic. Tensor entry canonical lifts are NOT ring homomorphisms. Do not claim recursion or an asymptotic speedup based on this bounded interpolation release. Run `python -m pytest -q`, `python scripts/validate_v28.py`, and `python scripts/verify_manifest.py` (after building release).

## v2.7 engineering constraints

Preserve all v2.6 source and backward compatible APIs. Treat `eth_modes_v27` as an experimental finite scalar reference only. NEVER label it a complete D.4.4 implementation or claimed subexponential solver. Any change to 2-adic pruning must pass a separately implemented Cauchy reconstruction checker and full small-network contraction comparisons. Resource budgets fail closed. See docs/D44_FINITE_MODES_V27.md.

# Current project policy (v2.5.0)

All work must preserve v2.4 backwards compatibility, keep `MANUSCRIPT_EXACT`
separate from `EXPERIMENTAL_SCALED`, independently check all packet claims,
and NEVER claim subexponential complexity without verified implementation
of the actual D.3 and D.4.4 proof obligations. See
`docs/ETH_V25_MATHEMATICAL_SCOPE.md`.

# v2.4 engineering invariants

- Treat the proof-checked weighted counting DAG as an arithmetic circuit. Compute
  exact marginal derivatives with a zero-safe reverse pass, never floating point
  nor division by individual weight values.
- All prior weight pairs must sum to one. For zero-probability evidence return
  UNDEFINED, not fabricated posteriors.
- Replay and independently check the entire DAG and all posterior values before
  asserting proof-checked evidence. Bind the certificate to the formula, prior,
  and DAG. Resource exhaustion returns UNKNOWN, not a partial answer.
- Never represent this as implementing D.3/D.4.4 or subexponential SAT solving.

---

# v2.3 engineering invariants

- Maintain exact Fraction arithmetic; never convert proof values to floats.
- `weights` entries are **[false,true]** nonnegative rational strings; missing
  variables mean [1,1] and are not normalized for probability queries.
- Verify CNF and weight digest bindings; recompute **every** DAG node from the
  original CNF and actual weights. Fail closed on incomplete proof construction.
- Conditioning requires normalized weights for every original variable and
  returns UNDEFINED on a zero-probability evidence event.
- All evidence levels must reflect a successful independent certificate check.
- This does not implement D.3 or D.4.4 of the claimed ETH algorithm.
- Test with `pytest`, `validate_v23.py`, inherited `validate_10000.py`, and
  re-extract the release ZIP and rerun manifest verification.

---

# v2.2 release invariants

Maintain correct counts over **all declared variables**, including unmentioned
ones. The DAG verifier must not trust purported residual formulas or accept
partial or cyclic proofs. Preserve strict node/byte/time bounds in generation,
fail closed on budget exhaustion, and perform differential checking against
exhaustive counting. Certificate checking runs in-process and has no hard
OS-enforced CPU budget; do not expose directly to untrusted clients.

The DAG result is not the manuscript's D.3 packing theorem, D.4.4 recurrence,
or a subexponential algorithm. Use `docs/COMPONENT_COUNT_DAG_V22.md`.

---

# v2.0.0 implementation boundaries

The exact matching optimizer only solves the **finite two-wire incidence
collision objective**. Verify global claims against subset DP for <=16 wires.
At larger sizes, label the optimum theorem-backed but externally computed,
not independently proof checked. Do not claim equivalence to paper D.3,
actual Cauchy runtime improvement, or asymptotic complexity gains.

Preserve backward compatibility of the API and CLI. Enforce n<=128 wires for
API and default Python calls; explicitly allow <=256 only from Python. Never
use the request timeout to imply a hard wall-clock stop inside NetworkX.
Validation gate: full pytest, `scripts/validate_v20.py`, legacy 10k
regression, smoke test, extracted archive replay, SHA256 manifest verification.

---

## v1.9.0 correctness and scope guardrails

Preserve every prior v1.8 entrypoint and test. Scalable packet optimizer
provides a feasible schedule and a globally valid lower bound on the same
**engineering incidence score**. It is not the paper's D.3 packing lemma.
The returned `exact_optimum` flag is allowed only when independent checker
recomputes BOTH lower bounds and verifies equality. Never treat a positive
`pair_gap` as evidence that the schedule is suboptimal; the bound can be loose.
On budgets, return a checked incumbent (not a purported optimum). Test score
incremental updates against original `collision_score` and test lower-bound
soundness against independent exhaustive-permutation oracles. Cauchy checks
must use the same relabeled network. Do not claim SAT speedups based only on
improved packet incidence scores.

Required gates: `pytest -q`, `scripts/validate_v19.py`,
`scripts/validate_10000.py`, `scripts/smoke.py`, extracted ZIP tests,
manifest verification.

---

## v1.8.0 priorities

Keep the v1.7 code and tests. The new `optimal_packets.py` implements a globally optimal **finite surrogate incidence-score** optimizer, never the claimed D.3 packing theorem. Preserve its timeout and workload budgets, and its small independent brute-force permutation oracle. The Cauchy research path must compare deformed results on the identical relabeled network. No subexponential algorithm claim is authorized by these upgrades.

# VERITAS-ETH v1.7.0 engineering guardrails

- Keep v1.6 functionality intact. The exact subset-DP planner only optimizes
  a dense cost proxy on <=12 original-CNF variables; it is not a real-runtime
  optimum or a result about the paper's D.3/D.4.4 theorem.
- Work objective: minimize sum(2**(filled_degree+1)), width as tie-break.
  Width objective: minimize peak filled degree, then minimize work under that
  globally minimum width constraint. Do not replace the two-pass DP with
  incorrect suffix-lexicographic optimization.
- Reject oversized inputs and deadlines with UNKNOWN, no partial counts.
- Verify all plans against independent graph-fill replay, verify CNF exact
  counts with exhaustive and sparse/dense references, and never treat a
  modular residue as the full integer count.
- Do not claim generic end-to-end performance improvement from a lower proxy
  score; benchmark planning plus execution, with reproducible inputs.
- No paper-specific subexponential implementation is present.

Required tests: `pytest -q`, `python scripts/validate_v17.py`,
`python scripts/validate_10000.py`, `python benchmarks/v17_optimal_order.py`,
`python scripts/smoke.py` and release manifest verification.

---

# VERITAS-ETH v1.6.0 coding agent requirements

Source baseline is v1.4.0, with v1.5 modules in `src/veritas/research/`. Keep original CNF and COPY3 conversion count-preserving, including empty clauses, tautologies, repeated literals, isolated declared variables and modular precision. Verify every graph decomposition using coverage, edge coverage, acyclicity and running intersection. End-to-end execution must return `UNKNOWN` on any cap or timeout; never publish partial counts or interpret residues as full exact counts. Retain the v1.4 min-degree API for compatibility; use true min-fill only in the new planner. The currently included slicing, small separators, and dense lookup are all treewidth-dependent and have exponential worst-case complexity. No paper-specific subexponential algorithm is implemented.

Validation: `pytest -q`, `python scripts/validate_v15.py`, `python scripts/validate_10000.py`, `python scripts/validate_v14.py`, `python scripts/smoke.py`, and deterministic ZIP SHA-256 integrity verification. Record wall-clock baselines honestly; planning overhead can dominate.

---

# Coding agent guidance: VERITAS-ETH v1.4.0

New `research/bounded_degree.py` supplies a parsimonious COPY3 equality-chain
CNF-to-tensor reduction that supports arbitrarily many appearances of a given
variable subject to explicit output size caps. The associated exact
`research/minfill_contract.py` is a deterministic min-neighbor heuristic and
an **exponential worst-case** bounded oracle. These are NOT the paper's
count-preserving sparsification theorem, D.4.4 collision packing algorithm,
or subexponential tensor contraction. Do not promote research checks into
proof certificates or cite passing tests as ETH theorem verification.

Each original variable assignment must have exactly one extension to all
auxiliary wires; isolated variables contribute two. Every wire appears in
exactly two tensor ports; every gadget degree is at most 3, separately from
clause width. Enforce bounded input, intermediate table and elapsed-time
caps and reject incomplete results. Prefer `python -m pytest -q`,
`python scripts/validate_v14.py`, `python scripts/validate_10000.py`,
`python scripts/smoke.py`, and ZIP manifest verification before releases.

More: `docs/BOUNDED_DEGREE_V14.md`.

---

# Coding agent guidance: VERITAS-ETH v1.3.0

The new `research/weighted_recovery.py` unifies weighted child-tensor local jets with exact modular Hermite interpolation. It is a bounded exact #SAT research reference, **not** the paper's subexponential ETH algorithm. Never call the transcript hash a mathematical proof. Only independent recomputation supports `RESEARCH_CROSS_CHECKED`. Guard precision must be checked before modulo arithmetic. Resource failure must return `UNKNOWN` with no partial result.

Required release checks: `python -m pytest -q`, `python scripts/validate_v13.py`, `python scripts/validate_v12.py`, `python scripts/validate_10000.py`, `python scripts/smoke.py`, and archive manifest verification. Details: `docs/WEIGHTED_RECOVERY_V13.md`.

# Coding agent guidance: VERITAS-ETH v1.2.0

Treat the v1.2.0 code as an **exact small-reference research platform**, not a completed ETH-breaking algorithm. Do not label mathematical claims proof-checked unless an independent verifier checks the actual proof artifact. The Lean proof was not rebuilt in this project. All changes must retain strict input limits and fail closed (`UNKNOWN`) rather than returning partial results.

Key new code: `src/veritas/research/weighted_children.py`. The coefficient-wise rational mode decomposition is *not* the paper D.4.4 weighted mode bound; the recursive child tensor implementation is a conventional exact boundary contraction, with worst-case exponential space/time in width. It reconstructs the kernel and then contracts polynomial-valued factor tables; it does not exploit manuscript-specific child-network compression.

Required validation after edits: `python -m pytest -q`, `python scripts/validate_v12.py`, `python scripts/validate_10000.py`, `python scripts/smoke.py`. All additions should use independent exact-count or Cauchy-jet oracles on bounded tests, deterministic seeds, explicit precision/degree/budget constraints, and transparent status labels. Review `docs/IMPLEMENTATION_STATUS.md` and `docs/WEIGHTED_CHILD_TENSORS_V12.md` before claiming a capability.

## v2.1 caution

Do not conflate `bounded_partition.py` finite collision proxy with the
manuscript's D.3 packing theorem. Search completion is *internal* evidence
unless an independent subset-DP oracle has also checked the result.

## v2.6 mathematical contract

Do not claim ETH is broken or asymptotic performance certified. The `eth_packing_v26` module establishes finite D.3 invariants only. Never merge the older `eth_packing` load-only heuristic or generic `packet_schedule` collision objective into claims about Appendix D.3. Run `pytest`, `scripts/validate_v26.py`, `scripts/smoke.py`, and `scripts/verify_manifest.py` before releases. The v2.6 parameter correction uses *ceil* rather than *floor*, and `eligible` checks only numeric D.6 when `M` and `delta` are explicit.


## v3.1 constraints
- Do not claim theorem-eligible packing or shrinking D.4.4 recursive child networks from finite v3.1 scalar children.
- Recompute exact mode coefficients from the original kernel; no approximate floating-point arithmetic.
- Every new research result must pass independent half-edge comparisons and hard resource limits.

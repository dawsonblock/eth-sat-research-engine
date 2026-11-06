# VERITAS-ETH: Full Implementation Plan

**Version:** 1.0 design specification  
**Date:** 2026-10-29  
**Status:** Proposed architecture and acceptance tests; not a claim of a completed implementation  
**Primary goal:** Build a reliable, auditable symbolic-reasoning engine for AI and independently reproduce/benchmark selected methods from OpenAI's October 25, 2026 ETH manuscript.

## 1. Architecture and non-negotiable engineering rules

Two separate tracks share a canonical constraint representation and testing infrastructure:

- **Production track:** natural-language statement to a reviewable, typed formal specification; established SAT, SMT, and exact #SAT backends; witness verification; independent proof checking where a compatible certificate exists; auditable output.
- **Experimental track:** reproduce the paper's exact-counting and algebraic primitives, then construct and test a constrained Boolean tensor-network solver; never allow the experimental backend to replace or override production verdicts without passing independent correctness and performance gates.

A successful tool invocation is **not** a proof. A valid model is a checkable certificate of SAT. An UNSAT result needs an independently checked proof artifact to be tagged `PROOF_CHECKED`; absent that, report `SOLVER_REPORTED_UNSAT`. A count from an exact model counter is `EXACT_SOLVER_RESULT`, not automatically a formally verified count. Two independent counters agreeing provides corroboration, not a mathematical certificate. Natural-language-to-logic translation is an additional uncertainty boundary: a checked theorem about the wrong formalization does not validate the original claim.

### Core result schema

- `request_id`, `input_sha256`, `canonical_ir_sha256`, `encoding_map_sha256`
- `problem_type`: `SAT|SMT|EXACT_COUNT|WEIGHTED_COUNT|PROOF_AUDIT|ETH_EXPERIMENT`
- `status`: `SAT|UNSAT|COUNT|UNKNOWN|TIMEOUT|ERROR|TRANSLATION_REVIEW_REQUIRED`
- `evidence_level`: `WITNESS_CHECKED|PROOF_CHECKED|CROSS_SOLVER_AGREEMENT|SOLVER_ONLY|RESEARCH_ONLY|NONE`
- `claim_ids`, `formal_assumptions`, `interpreted_terms`, `unresolved_ambiguities`
- `count`: decimal string or null; `count_semantics`: `all_declared|projected|weighted`
- `solver_id`, `solver_version`, `config_sha256`, `wall_time_ms`, `peak_rss_mb`
- `model`, `proof_artifact`, `counterexample`, `replay_command`, `audit_sha256`
- `explanation`: derived from checked structured result and tagged assumptions, not free-form invention.

## 2. Stack and environment

- **Development machine:** Windows 11 host with WSL2 Ubuntu; CPU-first local solvers, GPU only for optional LLM interpretation. Existing RTX 3080 Ti is ample for this role; a new 5090 is not a prerequisite. Use `ulimit`/cgroups/Docker resource caps and enforce a strict job queue.
- **Language:** Python 3.12+ for orchestration and verification harness; Rust for performance-critical parser/IR/experimental arithmetic once profiling justifies it; optional C++ backends wrapped in subprocesses.
- **Orchestration:** FastAPI + Pydantic validation, a local job runner, SQLite (single-user MVP) then PostgreSQL if multi-user; structured JSON logs and Prometheus metrics. Optional Qdrant stores retrieval-only source text; it never stores authoritative proof state.
- **Frontend:** Streamlit for initial tests; React/Tauri for desktop later. Must support keyboard, voice-dictation, paste, and file upload.
- **Solvers:** PySAT (CaDiCaL/Glucose backend as supported), Z3 for SMT, Ganak `--mode 0 --prob 0` for independent exact unweighted counts, CryptoMiniSat for XOR-heavy comparisons; a second model counter or brute-force oracle for cross-validation. For UNSAT certificate paths use solver-compatible DRUP/DRAT/LRAT proof output with a dedicated checker. Validate the actual produced format before selecting a checker.
- **Formal proofs:** Lean 4 via `elan`/`lake`, commit-pinned OpenAI `math` repository, pinned dependencies, isolated build. Build targeted targets, not the entire monorepo by default.
- **Testing:** pytest, Hypothesis, differential tests, mutation tests, fuzzed DIMACS parsers, deterministic benchmark runner, reproducible CI container.
- **Artifacts:** DIMACS CNF, SMT-LIB2, proof traces, JSON reports, perf CSV/Parquet, SHA-256 manifest.

## 3. Repository structure

```text
veritas-eth/
  README.md
  pyproject.toml
  docker-compose.yml
  configs/
    development.yaml
    production.yaml
    research.yaml
  docs/
    ARCHITECTURE.md
    THREAT_MODEL.md
    FORMALIZATION_POLICY.md
    PROOF_STATUS.md
    PAPER_TO_CODE_MAP.md
    BENCHMARK_PROTOCOL.md
  src/veritas/
    api/
    schemas/
    ingestion/
    claims/
    typed_ir/
    encoders/cnf.py
    encoders/smtlib.py
    encoders/provenance.py
    solvers/pysat_adapter.py
    solvers/z3_adapter.py
    solvers/ganak_adapter.py
    solvers/cryptominisat_adapter.py
    verification/witness.py
    verification/proof_checker.py
    verification/count_oracle.py
    verification/semantic_review.py
    orchestrator/router.py
    audit/manifest.py
    ui/
  research/
    paper_sources/
    proof_audit/
    arithmetic/boolean_polynomials.py
    arithmetic/parity_polynomial.py
    arithmetic/two_adic.py
    algebra/finite_differences.py
    algebra/hermite_interpolation.py
    algebra/linear_projection.py
    tensor/network.py
    tensor/cnf_to_tensor.py
    tensor/brute_contract.py
    tensor/mode_expansion.py
    tensor/recursive_contract.py
    reductions/sparsification.py
    reductions/variable_maps.py
  tests/
    unit/
    property/
    differential/
    regression/
    adversarial/
  benchmarks/
    instances/
    manifests/
    scripts/
    reports/
  scripts/
    verify_environment.sh
    audit_lean.sh
    smoke_test.py
    benchmark_all.py
```

## 4. Roadmap, milestones and release gates

### M0 — Freeze source and scope

1. Capture current OpenAI `math` commit SHA, file hashes of manuscript and all included LaTeX files, `lean-toolchain`, `lake-manifest.json`, and relevant comparator file.
2. Create the list of claims: paper's general theorem, October 25 sharper theorem, Lean comparator's weaker theorem, Boolean tensor contraction, and supporting reductions; record exactly which claims are formalized.
3. Record transformation assumptions: fixed clause width, declared-variable semantics, isolated/unused variables, count preservation, bounded tensor-degree/size/entry evaluation, modulus, and runtime parameter.
4. Write a threat model: misleading natural-language formalizations, malformed DIMACS, malicious solver output, resource exhaustion, untrusted research files, and audit-log tampering.

**Gate:** Source and claim-to-proof matrix complete; no ambiguous theorem statement; reproducible source hashes.

### M1 — Baseline symbolic engine

1. Implement typed Booleans, finite-domain integers, Boolean operators, equality, comparisons, quantifier-free arithmetic, and explicit assumptions.
2. Implement strict DIMACS CNF parser/serializer and SMT-LIB2 serializer. Retain named primary variables and distinguish auxiliary variables.
3. Launch PySAT for Boolean SAT and Z3 for SMT. Record `sat/unsat/unknown`, stdout/stderr, version, wall time, peak RSS, and warnings.
4. Re-check every SAT model by evaluating the original typed formula and its encoded CNF.
5. Add a solver-adapter conformance suite: known SAT/UNSAT problems, empty formula, empty clause, tautologies, duplicates, unused variables, nontrivial variable identifiers.

**Gate:** 100% correct witness checks on a deterministic exhaustive corpus with n<=16; no false proof-checked status; timeout returns `UNKNOWN` or `TIMEOUT`, never `UNSAT`.

### M2 — Natural-language formalization and provenance

1. Have the model return a structured collection of claims, entities, types, premises, conclusions, ambiguities, and optional user approvals.
2. Compile only schema-valid typed claims into logic. Separate observed data from assumptions, and hard from defeasible constraints.
3. For each logical clause store source-claim ID and transformation trace. Display an editable formal interpretation before relying on its verdict for high-impact questions.
4. Run contradiction checks via `premises AND NOT(conclusion)` and counterexample search.
5. Encode uncertainty honestly: a valid formal proof verifies only the selected formalization.

**Gate:** Golden test suite of 100+ controlled language-to-logic examples; ambiguous translations are surfaced instead of silently chosen; no generated solver tool commands executed directly from model text.

### M3 — Auditable verification

1. Support proof logging from compatible SAT backends.
2. Independently run a checker for the output format (DRUP/DRAT/LRAT). Check the proof against the canonical CNF hash.
3. For SAT results, verify the model from scratch. For SMT results, validate models when feasible; distinguish SMT UNSAT cores from complete proof certificates.
4. Store all evidence and replay scripts in a content-addressed immutable manifest.
5. Provide statuses `PROOF_CHECKED`, `WITNESS_CHECKED`, `SOLVER_ONLY`, `UNKNOWN`.

**Gate:** Corrupting proof bytes causes a failed verification; proof for another formula is rejected; stale or mismatched variable maps fail closed.

### M4 — Exact model counting

1. Implement reference brute-force #SAT oracle for n<=22 (smaller for CI) using arbitrary-precision integers.
2. Integrate Ganak with explicit `--mode 0 --prob 0` for exact unweighted, non-probabilistic counting, and a second independent count backend where practical.
3. Enforce clear semantics for all declared variables, projection variables, and auxiliary variables. Check 0 <= count <= 2^n for ordinary unweighted all-variable count.
4. Compare counts with brute force on a broad small-instance corpus and with an independent exact counter on a larger corpus.
5. Implement count-guided witness discovery and uniform sampling via self-reduction on a restricted, validated Boolean fragment. Avoid claiming probability from raw counts without a justified distribution.

**Gate:** Zero mismatches in 10,000 seeded small random/adversarial cases; any mismatch blocks production. For large instances where independent validation is impossible, preserve `EXACT_SOLVER_RESULT` status rather than `PROOF_CHECKED`.

### M5 — Lean proof reproduction and audit

1. Pin the OpenAI math commit and inspect `lean/README.md`, `lean/docs/378.md`, comparator and library build instructions.
2. Build only the relevant formalization dependencies in a reproducible Linux environment.
3. Identify the exact exported theorem and inspect its complete statement. Enumerate axioms with Lean's native mechanisms, check for `sorry`/`admit` and other proof escape hatches, and ensure relevant proof files genuinely compile.
4. Verify whether the formal theorem covers the claimed algorithm, its time bound, polynomial-space bound and input representation. Produce a comparison table against every manuscript theorem.
5. Record findings without interpreting a successful compiler exit as a proof of the stronger, different manuscript bound.

**Gate:** Clean targeted build, trustworthy theorem statement, documented axioms, reproducible verification command and machine manifest.

### M6 — Experimental algebraic counting primitives

Implement independent pure functions for:

1. Clause satisfaction indicator polynomials.
2. The parity indicator polynomial p_l(Y) and modular congruences on positive and negative integers.
3. 2-adic valuation and truncation under modulus 2^P; no floating-point approximations.
4. Boolean finite differences / Mobius coefficients.
5. Hermite interpolation and exact rational/integer arithmetic; prove input interpolation data are sufficient before reconstruction.
6. Bounded-occurrence/count-preserving preprocessing and exact variable mapping.
7. Projection/measurement construction in small toy dimensions and interpolation-node separation properties.

**Gate:** Each primitive passes property tests and exhaustive toy inputs. For transformed CNF counts, compare every result against pre-transformation brute-force counts. One counterexample to count preservation is release-blocking.

### M7 — Minimal Boolean tensor network

1. Define a network as a bipartite multigraph; each edge is one Boolean bit; each vertex has an ordered tensor table; support repeated edges with distinct ports.
2. Build `CNF -> tensor` via clause satisfaction tensors plus equality trees for repeated occurrences of one logical variable; add factors for declared-but-unused variables.
3. Implement brute-force tensor contraction as a reference oracle.
4. Evaluate over Z/(2^P) for P=n+1, tracking exact integer residue; ensure contraction yields original #SAT after accounting for unused variables.
5. Implement tree decompositions as a baseline optimization, but do not call these the paper's ETH algorithm.

**Gate:** 100% equivalence between direct #SAT, network brute contraction and reference exact counter on the finite oracle corpus. Include high-degree variables, repeated literals, parallel ports and isolated vertices.

### M8 — Reproduce tensor deformation and recursive contraction

1. Follow the paper's `quantitative-reduction.tex` and tensor appendix theorem-by-theorem. Implement polynomial wire deformation, local grouping, and interpolation values with exact arithmetic.
2. Implement formal mode-weight accounting: monomials removed only when guaranteed to vanish modulo 2^P. Log the exact divisibility argument and precision budget for every discarded term.
3. Implement recursive child contraction; each child must correspond to the proof's smaller-network case, including representation-size and entry-evaluation assumptions.
4. Instrument actual recursion depth, effective wire count, modes retained, bit-size growth, memory and runtime.
5. Validate each stage against brute-force tensor contraction on tiny networks and against an independently implemented unoptimized version on manageable networks.
6. The reported asymptotic theorem uses restrictive structural assumptions (input graph, bounded degree, representation length, local tensor evaluation and ring Z/(2^P)[V]/(V^ell)); enforce them explicitly.

**Gate:** Exact equivalence for all feasible toy networks and a formally traceable paper-to-code mapping. If an essential construction is underspecified, stop at a labeled partial reproduction; never replace it with a heuristic under the same algorithm name.

### M9 — Benchmark and evaluate

Define three suites:

- **Correctness:** all small 3-CNF instances from seeded generators, pigeonhole/coloring/graph encodings, XOR-heavy formulas, cases with unused variables, count-preserving reductions, independently verified expected counts.
- **Performance:** fixed n with controlled clause density, fixed m/n with increasing n, structured versus random hard cases, bounded-occurrence versus dense formulas.
- **Research internals:** network size, recursion exponent proxy, maximum intermediate precision, retained mode count, peak allocations, coefficients' bit-length, preprocessing overhead.

For every instance run reference brute force where feasible, exact model counter, optimized established SAT solver, and the paper-inspired prototype. Freeze CPU affinity, timeout, memory limit, environment, seeds and source commits. Record wall clock and CPU time, peak RSS, initialization, preprocessing, and solve time separately. Report failures, timeouts and censored samples; never plot an apparent speedup from completed runs while excluding timeouts. Use geometric mean only over an explicit common solved subset and report solved counts.

**Gate:** No correctness mismatch; positive throughput gain over a baseline on a preregistered representative dataset, not cherry-picked samples, before claiming practical benefit. Asymptotic complexity cannot be established by finite benchmarks.

### M10 — Product integration and release

1. Add a deterministic router: the production path handles real user requests; the research path is available only when explicitly selected.
2. Provide an evidence view for every answer: original claims, formal interpretation, solver result, checked witness/certificate, counterexample, and limitations.
3. Add policy-controlled cancellation, per-job CPU/RAM caps, RBAC if remote, network disabled for untrusted solver jobs, upload validation, and signed/verifiable audit entries.
4. Expose a local HTTP API and a desktop-compatible web app; keep model API credentials in a secret store, not exported logs.
5. Tag release `v1.0` only after correctness, regression, security and reproducibility gates pass. Experimental solver remains labeled alpha independent of production release.

**Gate:** End-to-end demonstrations with replayable evidence, one-click export, no use of an unverified research result as a production conclusion.

## 5. Core algorithms and mathematical invariants

### CNF indicator
For clause with positive and negative literals, write its Boolean satisfaction indicator as `1 - product(falsified_literal_indicator)`. On any Boolean assignment the value must be exactly 0 or 1. The product over clauses is 1 exactly for satisfying assignments; summing across all 2^n assignments yields the count.

### Count preservation
For each transformation T of formula F, explicitly record whether the invariant is: `#T(F) = #F`, or `#F = sum #T_i(F)` (disjoint branching), or `#F = #T(F)/factor`, or `#F = projected_count(T(F))`. Use exactly the invariant proved. A satisfiability-preserving Tseitin encoding is not necessarily count-preserving when counted over all variables without further restrictions.

### Tensor invariant
Original network contraction `Z = sum_{edge assignments} product(vertex_tensor_values)` equals the number of satisfying assignments to occurring variables. Multiply by `2^unused` for declared, unused variables. Work modulo `2^(n+1)` to uniquely recover 0 <= #F <= 2^n.

### Interpolation invariant
For a deformed polynomial H(T), verify `H(0)=#F`, the exact degree bound, node list, interpolation multiplicities, and rational/integer domain assumptions. No interpolation from insufficient samples.

### Two-adic invariant
A discarded term must be divisible by the current modulus `2^P` (or vanish after the mandated further operations). Model truncation as a checked algebraic rule, never a floating-point tolerance.

### Recursion invariant
At each recursive call, log network input size, ring precision, tensor evaluation cost, child wire size, stored state, and correctness relation. The paper's `2^(O(s/sqrt(log s)))` theorem pertains to a specified network class, not unrestricted arbitrary tensors.

## 6. Formalization policy for AI-generated claims

When given prose, the AI must: extract propositions; define entities/types; list explicit premises, implicit assumptions and scope; generate an executable formal representation; show the user-readable paraphrase; and only then request a solver verdict. A proof of `A => B` under assumptions `A` is not evidence that `A` is true. Numerical evidence, causal inference and source credibility remain separate from logical validity.

Examples of supported queries:

- "Do these three stated premises logically entail the conclusion?" Return a derivation/proof certificate if available, or a countermodel.
- "Are these requirements mutually consistent?" Return witness or checked UNSAT proof.
- "How many configurations satisfy these constraints?" Return exact unweighted count with declared count semantics.
- "Which assumption causes the contradiction?" Return a candidate/minimized unsatisfiable core, explaining that an SMT UNSAT core is not automatically a full independently checked proof certificate.

## 7. API contract

Suggested endpoints:

- `POST /v1/formalize` -> structured typed claims, assumptions, ambiguities, no solver verdict.
- `POST /v1/verify` -> `SAT|UNSAT|UNKNOWN`, witness/certificate status, provenance.
- `POST /v1/count` -> exact all-variable or explicit projected count, backend, certainty/evidence type.
- `POST /v1/counterexample` -> verified assignment refuting entailment.
- `POST /v1/paper/audit` -> formal theorem status and commit-pinned evidence.
- `POST /v1/research/contract` -> sandboxed experimental tensor job, research-only result.
- `GET /v1/jobs/{id}` and `POST /v1/jobs/{id}/cancel`.
- `GET /v1/audits/{hash}` -> full immutable/replayable package.

All requests have size caps and idempotency keys. Never execute arbitrary Python, shell, Lean scripts or code emitted directly from an untrusted LLM response on the host. Research code runs in a limited sandbox.

## 8. Verification and test matrix

| Test family | Purpose | Blocking failure |
|---|---|---|
| DIMACS round-trip fuzzing | Parser and serializer integrity | Semantic mismatch |
| SAT witness checker | Model correctness | Invalid accepted model |
| Unsat proof checker | Independently verify refutation | Invalid proof tagged checked |
| Count oracle n<=22 | Validate exact counts | Any different count |
| Projection/unused variables | Prevent auxiliary-variable overcount | Wrong counting semantics |
| Polynomial parity tests | Validate congruence modulo powers of 2 | Any counterexample |
| Exact interpolation | Check H(0) and coefficients | Wrong reconstructed value |
| Tensor conversion | Count-preserving CNF encoding | Any network mismatch |
| Mode-pruning fuzz tests | Preserve modular residue | Any wrong truncation |
| Timeouts & resource caps | Enforce fail-closed behavior | Timeout reported as theorem |
| Language formalization review | Prevent proof of wrong claim | Silent loss/addition of assumptions |
| Source-to-proof audit | Prevent overstating formalization scope | Stronger bound misrepresented as formalized |

Targets: 10,000 seeded small counting cases, 1,000 adversarial conversion cases, and 100+ controlled natural-language formalizations before production beta. These are engineering acceptance targets, not achieved results.

## 9. Quantitative scorecard

Keep the following release scoreboard:

- `semantic_translation_review_rate` and `silent_translation_change_rate` (target zero confirmed silent changes in golden set)
- `false_witness_acceptances` (target zero)
- `false_proof_checked_labels` (target zero)
- `exact_count_mismatches` (target zero)
- `timeouts_misclassified` (target zero)
- `benchmark_solved_count`, `median_latency`, `p95_latency`, `peak_rss`, `initialization_time`
- `count_by_n,m_density,network_wires`, `modes_retained`, `recursion_depth`, `max_coefficient_bits`
- `paper_claims_formalized`, `paper_claims_reproduced_in_code`, `open_assumptions_or_gaps`

No claimed runtime acceleration unless the research backend is both semantically correct and faster on representative preregistered tests under equal constraints.

## 10. Resource and operational strategy

Use the existing Windows PC + WSL2 and CPU for every mathematical prototype. SAT/SMT/counting workloads are not automatically GPU-bound, and purchasing a higher-end GPU before profiling would be premature. The optional local LLM parser may run on the existing 3080 Ti, or via an API. Start with 16-32 GB free host memory if available, cgroup-capped research jobs, CPU pinning for benchmarks, and disk for proof traces. Avoid large distributed infrastructure until the prototype demonstrates useful scaling.

Approximate development sequence for a single experienced engineer: first deliver the production SAT/SMT and witness validation path; then exact counting and evidence; then Lean audit; then arithmetic and tensor prototyping; only then the difficult recursive theorem reproduction. Treat durations as planning variables, not firm estimates: Lean dependency builds and manuscript-level reconstruction could dominate the project.

## 11. Dependency order and stop criteria

- **Do not start experimental recursion before M6 and M7 pass.** Otherwise failure origins will be impossible to localize.
- **Do not equate SAT-preserving encodings with exact-count-preserving encodings.** Track all primary versus auxiliary variables.
- **Do not tag an SMT unsat core a checked formal proof.** A core points to relevant assumptions, not necessarily a standalone certificate.
- **Do not equate the Lean comparator theorem with the sharper manuscript theorem.** Check the exact statement.
- **Do not optimize or buy hardware before profiling.** Mathematical uncertainty, not compute availability, is the main risk.
- **Stop any promotion of the research backend on a single reproducible count mismatch or undocumented algebraic shortcut.**
- **Stop claims of practical improvement if 95th-percentile latency, initialization time, or total cost is worse on representative inputs.**

## 12. Immediate first sprint: concrete tickets

1. `SRC-001`: Pin paper repository SHA, parse included `.tex` names, generate source manifest.
2. `SRC-002`: Build theorem/proof-scope matrix with a link to comparator theorem.
3. `CORE-001`: Define typed Boolean AST and canonical CNF writer preserving variable identity.
4. `CORE-002`: Implement PySAT adapter with timeout, model generation, and independent witness evaluator.
5. `CORE-003`: Implement direct exhaustive #SAT oracle and small random 3-CNF generator.
6. `CORE-004`: Integrate Ganak exact unweighted `--mode 0 --prob 0` and compare against oracle.
7. `VERIFY-001`: Prove that a verifier rejects a corrupted model and mismatched CNF digest.
8. `MATH-001`: Implement modular parity polynomial unit/property tests.
9. `MATH-002`: Implement CNF-to-tensor conversion and brute-force contraction.
10. `CI-001`: Publish one-command reproducible tests, exact backend version capture, manifest, and sample results.

At the end of the first sprint, the system must successfully explain and verify a small user constraint problem, count its models, and present a replayable evidence package. The recursive ETH-inspired solver remains unimplemented unless the foundational milestones pass.

## 13. Primary sources

- Paper: https://github.com/openai/math/tree/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026
- Lean scope: https://github.com/openai/math/blob/main/lean/docs/378.md
- Lean library guidance: https://github.com/openai/math/blob/main/lean/README.md
- Tensor theorem/reduction: https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-reduction.tex
- PySAT API: https://pysathq.github.io/docs/html/api/solvers.html
- Z3 documentation: https://microsoft.github.io/z3guide/
- Ganak: https://github.com/meelgroup/ganak
- DRAT-trim: https://github.com/marijnheule/drat-trim
- CryptoMiniSat: https://github.com/msoos/cryptominisat

## Definition of success

**Production success** is an evidence-oriented reasoning tool with correct semantics and independent verification where possible. **Research success** is a reproducible, non-handwavy implementation of paper components plus honest correctness and performance measurements. **Neither goal requires claiming a practical breakthrough from a purely asymptotic result.**

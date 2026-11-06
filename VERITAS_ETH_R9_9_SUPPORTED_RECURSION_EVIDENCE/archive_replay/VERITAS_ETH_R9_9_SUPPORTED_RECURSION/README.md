# R9.9 supported packet recursion development

This checkout adds a separate exact finite support executor for general
multi-slot packets, including shared modes with exponents above one. Complete
crossing-parent grids use real 64-group children and rational Hermite recovery.
A second finite path combines independently checked row-degree bounds with
actual shrinking recursive children and streamed evidence. Independent replay
reconstructs the children and recomputes their leaf values.

See [the mathematics, limits and external CLI](docs/R99_SUPPORTED_RECURSION.md).
The [validated release report](RELEASE_REPORT_R99_SUPPORTED.md) records the
actual recursion, independent replay and remaining obligations.
The original complete weighted stream remains available. Source-active
qualification, universal executable refinement and complexity proofs remain
open; theorem mode stays disabled.

## Historical R9.8 parent-to-child development

This checkout adds immutable 64-group children, independent packet/port verification,
complete weighted tuples, and bounded two-level scaled recursion with exact Hermite
recovery. The finite boundary engine remains separate. Source-active qualification,
termination refinement and asymptotic complexity are still open.

Package version: `3.8.2.post98`. See the [R9.8 release report](RELEASE_REPORT_R98.md) and
[implementation and limits](docs/R98_PARENT_CHILD_IMPLEMENTATION.md).
The signed one-edge recursive fixture returns 7 modulo 32 after 124,929 actual calls;
its nonshrinking children are explicitly recorded. It is not a source-regime result.

> **Historical R9.7 paper verification and portable finite execution.** That package version was
> `3.8.2.post97`. Added: a source-bound 64-group finite grid checker, independently
> checked boundary proof trees, explicit certified-elimination routing, and Lean
> table-gather/partition theorems. Source-active recursion and the general ETH theorem
> remain unavailable. [Release and commands](RELEASE_REPORT_R97.md) ·
> [Mathematical scope](docs/R97_PAPER_CONFORMANCE_AUDIT.md) ·
> [Finite execution and packaging](docs/R97_FINITE_EXECUTION.md).

> **Historical R9.6 finite reductions and evidence repairs.** Run exact bounded DIMACS counts with
> `python -m veritas.research.finite_reductions input.cnf` from an installed source checkout.
> The release includes checked child recipes, two complete finite interpolation grids, and
> replayable 12–16-wire reductions. [Results and reproduction](RELEASE_REPORT_R96.md) ·
> [Mathematical audit](docs/R96_REDUCTION_AUDIT.md).

> **R9.5 entry-execution partial release:** exact creation-time recipe evaluation,
> source-prescribed leaf contraction, an independent polynomial/elimination oracle,
> and Lean coordinate-lifting contracts. Active theorem recursion remains disabled.
> See [audit](docs/R95_SOURCE_MATH_AUDIT.md), [API](docs/R95_RECIPE_API.md),
> [release report](RELEASE_REPORT_R95.md) and [blockers](docs/R95_REMAINING_OBLIGATIONS.md).

> **R9.4 source-foundation partial release:** bounded source-state admission,
> kernel-checked keyed labeling-run correspondence and finite packet-domain
> cardinality. Full theorem execution remains disabled. See
> [release report](RELEASE_REPORT_R94.md), [audit](docs/R94_SOURCE_FOUNDATION_AUDIT.md)
> and [remaining obligations](docs/R94_REMAINING_OBLIGATIONS.md).

# VERITAS-ETH v3.8.2 — finite Hermite reconstruction reference

## R9.3 global packet model and executable checks

R9.3 adds kernel-checked occurrence-rank, numeric-slot, and computed-padding
proofs composed into a global packet-address model. Both Python packet builders
are checked against independent finite decoders and Lean evaluations. See
[`RELEASE_REPORT_R93.md`](RELEASE_REPORT_R93.md) and
[`docs/R9_3_PACKET_CORRECTNESS.md`](docs/R9_3_PACKET_CORRECTNESS.md).
The Python-to-Lean executable bridge and complete recursive counting theorem
remain unproved; theorem mode stays disabled.

## R9.1 C++20 backend and formal refinement upgrade

R9.1 adds an exact C++20 scoring backend (`cpp/`), a Lean transcription of the
CPython candidate scorer (`proofs/D3PythonScoreModel.lean`), and the packet
slot bijection (`proofs/D3PacketBijection.lean`). Read
[`RELEASE_REPORT_R91.md`](RELEASE_REPORT_R91.md) first, then
[`docs/R91_REFINEMENT_AUDIT.md`](docs/R91_REFINEMENT_AUDIT.md), which records
the CPython-to-model trust boundary and the remaining run-selection and
transition obligations. The Lean transcription's candidate-score identity
with `concreteD3ScoreCandidate` is kernel checked. That theorem does not prove
that CPython bytecode or the C++ executable refines the model. The C++ backend
is tested against the Python reference, **not** formally verified.

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp -j && ./build/cpp/veritas_d3_selftest
python -m pytest -q
python scripts/benchmark_r91_scorer.py
python scripts/validate_r91.py
```

## R8.2 finite verification upgrade

R8.2 adds an independent rational Cauchy/mode-action checker, bounded
coefficient and tuple-pruning audits, selected 4/6/8-wire parent-versus-child
point checks, and content-bound V3 finite execution transcripts. Start with
[`RELEASE_REPORT_R82.md`](RELEASE_REPORT_R82.md), the three R8.2 contracts in
[`docs/`](docs/R82_MATH_AUDIT.md), and the machine evidence in
[`validation/r82_release_evidence.json`](validation/r82_release_evidence.json).
These finite checks do not establish universal mode completeness, the paper's
multilevel recursion, its complexity bound, or theorem-qualified #SAT.

> **Git development snapshot:** This directory includes experimental work
> added after the original v3.8.2 archive. The historical release reports
> describe earlier artifacts, not this snapshot. The checked-in SHA-256
> manifests describe the current files; they are not signatures or proof of
> qualification. The [finite recursion experiments](docs/FINITE_TAPERED_RECURSION_V39.md)
> do not establish the manuscript's subexponential bound.

The source of the paper this reference implements is now vendored in
[`paper/`](paper/README.md), and
[`docs/OPENAI_PAPER_CONFORMANCE.md`](docs/OPENAI_PAPER_CONFORMANCE.md) maps
every component to its labelled lemma or equation. Use the pinned source labels;
the project's "D.3"/"D.4.4"/"D.6" names are historical aliases for
`app:tensor`, `lem:tensor-packets`, `subsec:tensor-children`, and
`eq:tensor-packing-conditions`. `tests/test_openai_paper_conformance.py`
asserts that the schedule, packing, tapered-Hermite, mode, and
count-recovery parameters against the pinned formulas within their test scope.
The correction to earlier appendix-numbering prose is recorded in
[`docs/R9_SOURCE_AUDIT.md`](docs/R9_SOURCE_AUDIT.md).

`src/veritas/research/eth_counting_v39/` implements the paper's other half,
`sec:counting` and `sec:construction` -- the low-degree replacement forms and
shared linear summaries -- and counts bounded-occurrence CNFs exactly by that
route. See [LINEAR_SUMMARIES_V39.md](docs/LINEAR_SUMMARIES_V39.md). It is a
finite reference: it reproduces exhaustive enumeration, not the paper's
running-time bound.

This release inherits the v3.8 review fixes and adds an exact finite
nonzero-node Hermite reconstruction check for dense L=2 Cauchy networks.
See [the v3.8.2 correction and evidence notes](docs/CORRECTIONS_V382.md) and
the inherited [v3.8.1 hardening notes](docs/CORRECTIONS_V381.md). The
v3.8.1 child-elimination certificate schema remains unchanged; old v3.8.0
certificates continue to be rejected. The shared work limit is cooperative,
counts selected events and does not enforce an OS-level time or memory bound.

This cumulative release retains v3.7 and adds a resource-bounded exact
**factor elimination** runtime for its fixed-mode D.4.4 group-local packet
tensors. It evaluates small child factors over exact 2-adic extension jets,
caches packet factor tables, decomposes disconnected child graphs, and checks
the result against independently computed direct Cauchy half-edge contraction.

The exact manuscript-side obligations and staged implementation gates are
mapped in [the Appendix D contraction roadmap](docs/APPENDIX_D_CONTRACTION_ROADMAP_V382.md).

**This is not the paper’s recursively regenerated D.4.4 tensor algorithm.**
The manuscript's depth-dependent precision propagation, universal M/8 bound,
and subexponential worst-case runtime are NOT implemented/proven.

```powershell
python -m pip install -e ".[test]"
veritas-eth38 construct --n 2 --clauses-json "[[1,2]]" --cross-check-v37 --output proof.json
veritas-eth38 check --certificate proof.json
python -m pytest -q
python scripts/validate_child_elimination_v38.py
```

API: `POST /v1/research/eth/finite-child-elimination`,
`POST /v1/research/eth/finite-child-elimination/check`, and
`GET /v1/research/eth/v38/status`. The browser UI has a matching demonstration.
See `RELEASE_NOTES_V38.md` and `docs/FINITE_D44_CHILD_ELIMINATION_V38.md`.

---

# v3.7 research reference addition

An exact, finite *group-local D.4.4 child packet tensor* reference is available in `veritas.research.eth_d44_child_reference`. Unlike v3.5's mode-bond representation, fixed mode exponents are metadata, not child wires. The resulting contraction identity is checked against an independent Cauchy oracle. This is not a subexponential solver. See `docs/D44_GROUP_LOCAL_CHILD_SOLUTION_V37.md` and `RELEASE_NOTES_V37.md`. Use `veritas-eth37` after installation.

# VERITAS-ETH v3.6.0

v3.6 adds **exact finite Cauchy packet tensors in the Boolean-multilinear basis**, replay checked by independent Boolean Möbius inversion and full half-edge contraction. Use `veritas-eth36 construct` or `/v1/research/eth/finite-packet-tensors`. All previous v3.5 functionality is preserved. See `RELEASE_NOTES_V36.md` and `docs/FINITE_CAUCHY_PACKET_TENSORS_V36.md`. **Not the manuscript D.4.4 recursive subexponential algorithm.**

# VERITAS-ETH v3.5.0

v3.5 adds independently checked finite child factor scopes and resource gates. See `RELEASE_NOTES_V35.md` and `docs/FINITE_CHILD_NETWORK_V35.md`. **Not a subexponential ETH solver.**

# VERITAS-ETH v3.4.0 — verified structural child preflight

**Cumulative source upgrade from v3.3.0**: independent D.3 symbol-port / packet-slot / geometric-mode incidence ledger, integrated linkage to v3.3 finite exact recursive mode-bond contraction, replayable certificates, API/CLI/UI, bounded seeded validation. See `docs/D34_STRUCTURAL_CHILD_TOPOLOGY_V34.md` and `RELEASE_REPORT_V34.md`.

These are **not** the manuscript's recursively shrinking child packet tensor networks. The `M/8` theorem and subexponential runtime are not established by this software.

```bash
pip install -e '.[test]'
veritas-eth34 construct --with-modes --output topology.json
veritas-eth34 check --certificate topology.json
veritas-eth34 contract --output combined.json
veritas-eth34 check --certificate combined.json
python scripts/validate_v34.py
```

---

# VERITAS-ETH v3.3.0 — finite recursive mode-bond contraction

New: exact recursive separator-style mode-exponent contraction, sparse conditioning, disconnected-component decomposition, deterministic memoization, triple-oracle source replay, CLI/API/browser integration and budgeted execution. See `docs/FINITE_RECURSIVE_MODE_BONDS_V33.md` and `RELEASE_REPORT_V33.md`. **Not** the manuscript D.4.4 recursively shrinking packet tensor algorithm or an ETH result.

```bash
python -m pip install -e ".[test]"
veritas-eth33 construct --n 2 --clauses-json "[[1,2]]" --output cert.json
veritas-eth33 check --certificate cert.json
python scripts/validate_v33.py
```

---

# VERITAS-ETH v3.2.0 — finite exact geometric-mode bond tensor network

**New in v3.2:** Sparse source/target group tensors indexed by shared geometric-mode exponents, exact sparse bond contractions over extension-ring Taylor jets, complete child-table certificates, independent half-edge validation, API/CLI/UI integration. See `RELEASE_NOTES_V32.md`, `docs/MODE_BOND_TENSOR_NETWORK_V32.md`, and `RELEASE_REPORT_V32.md`.

**Not the ETH theorem:** no recursively shrinking manuscript packet tensors, M/8 bound or subexponential algorithm has been verified. v3.2 is a bounded finite exact research implementation.

```bash
python -m pip install -e '.[test]'
veritas-eth32 construct --n 2 --clauses-json '[[1,2]]' --output mode-bonds.json
veritas-eth32 check --certificate mode-bonds.json
python scripts/validate_v32.py
```

---

**Full cumulative release based on v2.9.0.** New in v3.0: group-aware lazy tensor entry functions, bounded extension-ring Taylor child contractions, independent half-edge oracle, exact `T=0` count cross-check, replayable certificates, CLI and API/UI integration. See `docs/IMPLICIT_EXTENSION_CHILDREN_V30.md` and `RELEASE_REPORT_V30.md`.

**Mathematical limitation:** v3.0 does **not** implement the manuscript's D.4.4 geometric tile / mode-selected recursion, its `M/8` child shrinkage, or the claimed subexponential ETH algorithm. Every certificate states this explicitly.

```bash
pip install -e '.[test]'
veritas-eth30 construct --n 2 --clauses-json '[[1,2]]' --output child-cert.json
veritas-eth30 check --certificate child-cert.json
python scripts/validate_v30.py
pytest -q tests/test_v30_implicit_children.py
```

---

# VERITAS-ETH v2.9.0 — finite tapered Hermite and extension-ring modes

**Full cumulative upgrade from v2.8.0.** Adds valuation-tapered exact modular Hermite constant-term reconstruction and independently checked finite extension-ring rank-one Cauchy modes. Retains every previous SAT, #SAT, proof, packing, Cauchy, API, CLI and UI component. See [`RELEASE_NOTES_V29.md`](RELEASE_NOTES_V29.md), [`docs/TAPERED_EXTENSION_MODES_V29.md`](docs/TAPERED_EXTENSION_MODES_V29.md), and [`RELEASE_REPORT_V29.md`](RELEASE_REPORT_V29.md).

**Not implemented:** manuscript's specialized D.4.4 geometric tile-mode expansion over extension-ring Taylor coefficients, implicit recursive child tensors and subexponential contraction. The finite rank-one construction **must not** be described as the original asymptotic algorithm.

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v29.py
veritas-eth29 tapered --wires 2 --coefficients-json '[12,9,-3,0,2]'
veritas-eth29 modes --output research-mode-cert.json
veritas-eth29 check-modes --certificate research-mode-cert.json
```

Extract and run `start_windows.ps1` on Windows, then open `http://127.0.0.1:8080`. Windows startup has not been exercised in this Linux validation environment.

---

# VERITAS-ETH v2.8.0 — extension-ring interpolation upgrade

**Cumulative source release** from v2.7. Adds corrected floor-based Appendix D parameters, exact residue-separated finite-ring interpolation, canonical tensor-entry creation-time lifts and shifted Cauchy coefficient verification. See `RELEASE_NOTES_V28.md`, `docs/EXTENSION_INTERPOLATION_V28.md` and `docs/SOURCE_REVISION_DIFFERENCES_V28.md`.

**The ETH-breaking subexponential solver is NOT implemented.** Tapered Hermite, specialized implicit child networks and the manuscript's full recursive cost analysis remain separate tasks. The public manuscript source is not pinned to a commit.

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v28.py
veritas-eth28 cauchy --packet-size 2 --node 1 --precision 8 --extension-degree 4
```

On Windows run `start_windows.ps1` and open `http://127.0.0.1:8080`.

---

# VERITAS-ETH v2.7.0 — finite D.4.4 geometric modes

**Full cumulative upgrade from v2.6.0.** New independently checked scalar-mode factorization on verified D.3 packets, exact 2-adic valuation-based pruning, weighted exponent enumeration, and a full small-network deformed-contraction reference. See `RELEASE_NOTES_V27.md` and `docs/D44_FINITE_MODES_V27.md`.

**The subexponential ETH algorithm is NOT implemented.** The full extension-ring Taylor-jet mode construction, tapered precision, implicit child-tensor construction and recursive contraction remain research tasks.

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v27.py
veritas-eth27 construct --edges-json '[[0,0],[1,1],[0,1],[1,0]]' --a 1 --node 1 --output finite-modes.json
```

---

# VERITAS-ETH v2.5.0 — Experimental packing and exact coefficient-ring upgrade

**Cumulative upgrade from v2.4.0.** Adds bounded D.3-inspired packet
construction with independently checked finite structural and numerical
invariants, exact GF(2)/2-adic extension-ring arithmetic, truncated jets,
local Cauchy polynomial verification, and isolated API/CLI/UI tooling.

**No subexponential solver is implemented.** The *full* manuscript D.3
collision-packing theorem, complete recursive D.4.3 integration, D.4.4
weighted-mode recursion and end-to-end proof remain unimplemented. See
`docs/ETH_V25_MATHEMATICAL_SCOPE.md` for the exact completion matrix.

Run `python -m pip install -e ".[test]"`, `python -m pytest -q` and
`python scripts/validate_v25.py`; Windows: `start_windows.ps1`.

---

# VERITAS-ETH v2.4.0 — exact posterior marginal inference

**Full cumulative upgrade from v2.3.0.** One proof-checked weighted
component-DAG yields exact posterior probabilities for all declared Boolean
variables under explicitly normalized rational independent priors. The source
includes a second checker, REST endpoints, CLI and browser controls, seeded
exhaustive validation, and a standalone example. See `RELEASE_NOTES_V24.md`.

**Limit:** this remains conventional exact model counting with exponential
worst-case complexity; the manuscript D.3 packing lemma and D.4.4
subexponential recursion are **not implemented**.

## v2.4.0 — independently checked all-variable exact posterior marginals

Batch exact rational posterior inference from a single checked component-DAG with zero-safe reverse accumulation, independent certificate replay, API/CLI/browser support, and exhaustive seeded differential tests. See `RELEASE_NOTES_V24.md` and `docs/EXACT_POSTERIOR_MARGINALS_V24.md`. This is a conventional exponential-worst-case weighted counting algorithm, not the manuscript ETH recursion.

# Previous release: VERITAS-ETH v2.3.0 — verified weighted model counting and conditional probability

**Full cumulative upgrade from v2.2.0**, retaining all prior research and
verification modules. v2.3 adds exact rational weighted model counting with
component-DAG certificates, and exact conditional probabilities under
independent normalized Bernoulli priors. A dedicated checker reconstructs all
CNF residual states and rejects altered weights or node counts. These are
bounded exponential-worst-case algorithms; **the ETH subexponential recursion
remains unimplemented**.

Quick start on Windows: `./start_windows.ps1`, then open
`http://127.0.0.1:8080`. See `docs/WEIGHTED_COUNTING_V23.md` for JSON weights,
API, CLI and proof semantics. Run `python scripts/validate_v23.py` and
`python -m pytest -q` for validation. See `RELEASE_REPORT_V23.md` for results.

---

# VERITAS-ETH v2.2.0 — proof-checked component-DAG #SAT

**Full cumulative upgrade from v2.1.0.** New exact, memoized model counter
with component factorization and a replayed counting DAG certificate. It
preserves every previous API, CLI tool, test, and experimental module.

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v22.py
python scripts/validate_10000.py
python benchmarks/v22_count_dag.py
veritas-cli cnf examples/example.cnf --certify-count-dag
```

Run `start_windows.ps1` on Windows or `./start.sh` on Linux/WSL; open
`http://127.0.0.1:8080` and select *Proof-checked component DAG #SAT (v2.2)*.

See [mathematics and API](docs/COMPONENT_COUNT_DAG_V22.md) and
[release audit](RELEASE_REPORT_V22.md). The algorithm remains **exponential
worst case**, and the paper's D.3 packing / D.4.4 subexponential recursion
is **not implemented**.

---

# VERITAS-ETH v2.1.0 — New bounded packet branch-and-bound

**v2.1 addition:** finite packet partition search (sizes 1/2/4/8),
provably admissible collision bounds, independent score checker,
explicit incomplete-search evidence. See `docs/BOUNDED_PARTITION_V21.md`
and `RELEASE_REPORT_V21.md`. This does **not** implement manuscript D.3/D.4.4.

# VERITAS-ETH v2.0.0 — exact pair-packet global optimization

**Cumulative upgrade of v1.9.0.** Preserves the exact SAT/#SAT, certificate,
tensor-network, Cauchy/Hermite and prior packet optimizers. Adds an exact
polynomial-time solver for the finite **packet_size=2 collision surrogate**
using weighted perfect matching (Blossom via optional NetworkX).

```bash
python -m pip install -e '.[test,matching]'
python -m pytest -q
python scripts/validate_v20.py
python scripts/validate_10000.py
python benchmarks/v20_matching.py
veritas-cli cnf examples/example.cnf --matching-packets --packet-size 2
veritas-cli cnf examples/example.cnf --cauchy-eliminate --optimize-packets --packet-optimizer matching --packet-size 2
```

Alternatively run `start_windows.ps1` on Windows or `./start.sh` on Linux/WSL,
then browse to `http://127.0.0.1:8080` locally. Those scripts install the
optional matching dependency. The matching optimizer is limited to 128 wires
by default, allows up to 256 explicitly from Python, and supports packet
size **2 only**. `timeout_s` does not interrupt the third-party Blossom call;
for strict wall-clock limits, run it in a deadline-controlled subprocess.

**Evidence level:** The two-wire objective is mathematically equivalent to
minimum-weight perfect matching. For <=16 wires an independent subset-DP
oracle checks the optimizer. At larger sizes the reported global optimum
relies on the external Blossom algorithm, not an independently verified proof
certificate. The separately implemented checker validates the schedule and
objective but does not reproduce the full Blossom computation.

**Not implemented:** the manuscript's D.3 quantitative packing theorem,
D.4.4 weighted mode complexity recurrence, the full claimed subexponential
algorithm, or a locally verified Lean formalization. This release establishes
neither faster end-to-end counting nor an ETH breakthrough.

Details: [v2.0 mathematical and engineering specification](docs/EXACT_MATCHING_PACKETS_V20.md),
[release validation](RELEASE_REPORT_V20.md).

---

# VERITAS-ETH v1.9.0 — Scalable packet scheduling with independently checked lower bounds

**Complete cumulative upgrade from v1.8.0.** Adds a bounded multistart packet
optimizer that accepts larger incidence networks than the 16-wire exact DP,
computes a provable global lower bound for the finite collision surrogate,
and certifies surrogate optimality **only if the achieved score reaches that bound**.
An independent checker rejects forged scores/bounds/permutations. API, CLI,
browser, and the small Cauchy-jet backend can use the new planner. All prior
v1.8 features remain.

```sh
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v19.py
python benchmarks/v19_packet_search.py
veritas-cli cnf examples/example.cnf --scalable-packets --packet-size 4
veritas-cli cnf examples/example.cnf --cauchy-eliminate --optimize-packets --packet-optimizer scalable
```

Read [the v1.9 mathematical and engineering scope](docs/SCALABLE_PACKET_BOUNDS_V19.md)
and [the release report](RELEASE_REPORT_V19.md). The actual manuscript D.3
packing theorem and D.4.4 subexponential recursion **are not implemented**.
This finite objective improvement does not establish faster SAT solving.

---

# VERITAS-ETH v1.8.0 — Exact finite packet-partition optimization

**Full cumulative upgrade from v1.7.0.** Adds exact subset-DP optimization for the finite packet incidence-collision objective (up to 16 tensor wires), with independent objective replay, deterministic tie breaking, bounded failure behavior, an optional exact-packet mode for the existing Cauchy elimination research backend, and API/CLI/browser integration. All previous capabilities remain available.

```sh
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v18.py
python benchmarks/v18_packets.py
veritas-cli cnf examples/example.cnf --optimal-packets --packet-size 2
veritas-cli cnf examples/example.cnf --cauchy-eliminate --optimize-packets --packet-optimizer exact_dp
```

This is an **exact finite optimum for a surrogate score**, not the original manuscript's packing theorem. It does not prove or implement a subexponential ETH algorithm. Read [v1.8 specification](docs/EXACT_PACKET_PARTITION_DP_V18.md) and [release report](RELEASE_REPORT_V18.md).

---

# VERITAS-ETH v1.7.0 — Globally optimal small-instance contraction-order planning

**Complete cumulative upgrade from v1.6.0.** Adds an exact subset-DP optimizer
that finds a globally optimal dense-work order on the original CNF primal
graph for at most 12 variables, plus an exact minimum-width alternative,
independent order replay, a dedicated plan-analysis API, CLI and browser
operations, seeded validation and benchmarks. Default fast-first execution
remains unchanged because the optimal planner adds overhead.

```sh
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v17.py
python benchmarks/v17_optimal_order.py
veritas-cli cnf examples/example.cnf --optimal-order-report --optimal-objective work
veritas-cli cnf examples/example.cnf --adaptive-contract --adaptive-portfolio optimal_small
```

Run `./start_windows.ps1` on Windows PowerShell or `./start.sh` on Linux/WSL,
then open **http://127.0.0.1:8080**. Keep the service local to your machine.

The optimal ordering guarantee concerns a **mathematical cost proxy**, not
actual elapsed runtime. The optimization itself examines exponentially many
subsets and is limited to at most 12 variables. See
[exact order specification](docs/EXACT_ORDER_OPTIMIZATION_V17.md) and
[release report](RELEASE_REPORT_V17.md).

**This software does not implement or validate the claimed subexponential ETH
algorithm.** Manuscript-specific D.3 packing, D.4.4 weighted modes and complete
quantitative recursion remain unimplemented.

---

# VERITAS-ETH v1.6.0 — Fast indexed and sparse exact contraction

**Cumulative, runnable update to v1.5.0.** Adds indexed exact contraction, sparse hash-join factor contraction for sparse equality-heavy networks, quick-first portfolio planning with full fallback, and reproducible comparative benchmarks. Existing SAT, #SAT, proof certificates, Cauchy/Hermite experiments, API and UI remain included. The new `auto` planner accepts a feasible quick plan rather than always computing six candidates; it is not guaranteed to find the lowest-cost order. The default `indexed` executor is exact; `legacy` and `sparse` modes support independent comparison.

```sh
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v16.py
python benchmarks/v16_adaptive.py
veritas-cli cnf examples/example.cnf --adaptive-contract --adaptive-execution indexed
```

Details: [v1.6 exact contraction specification](docs/FAST_SPARSE_CONTRACTION_V16.md). **Not a subexponential ETH algorithm.** All original D.3/D.4.4 collision-packing and quantitative recursion milestones remain unresolved. Memory limits apply to encoded factor rows and modeled work, not hard OS process limits.

---

# VERITAS-ETH v1.6.0 — Adaptive exact contraction and bounded-memory planning

**Complete cumulative upgrade of the v1.4.0 project.** This release adds a deterministic exact #SAT execution planner, representation selection (original CNF variables versus COPY3 occurrence tensors), verified elimination-tree decompositions, true minimum-fill and weighted-fill heuristics, separator-conditioned boundary dynamic programming, exact memoization, and bounded index slicing. Includes a new browser console option, API endpoint, CLI flags, seeded validation, and side-by-side benchmark observations. **None of these techniques prove or implement the ETH paper's claimed subexponential contraction.** Worst-case runtime remains exponential.

### Start (Windows / Linux / WSL)

```powershell
# Windows PowerShell after extracting the ZIP
.\start_windows.ps1
```

```sh
# Linux / WSL / macOS after extracting the ZIP
./start.sh
```

Open **http://127.0.0.1:8080** and select **Adaptive exact #SAT planner + separators (v1.5)**. The server listens on loopback only. It is not configured or authorized for Internet exposure.

### Run tests and examples

```sh
python -m pip install -e '.[test]'
pytest -q
python scripts/validate_v15.py
python benchmarks/v15_adaptive.py
veritas-cli cnf examples/example.cnf --adaptive-contract --timeout 10
```

API endpoint: `POST /v1/research/adaptive-contract` (see `/docs`). Detailed mathematical scope, resource parameters, correctness requirements, and example JSON: **[v1.5 technical specification](docs/ADAPTIVE_CONTRACTION_V15.md)**.

**Verified limitations:** the planner and recursive decomposition may be slower than v1.4 for small or easy instances; four initial benchmark cases showed lower estimated operations but higher wall-clock time due to planning overhead. Memory limits are per dense table, not a hard OS-wide RAM limit. Cache memory and Python object overhead are bounded by entry counts but not process isolation. `COUNT_RESIDUE` is not an exact full integer count. Optional external decomposition planners, sparse factor tables, high-performance Rust kernels, general-purpose treewidth guarantees, and paper-specific D.4.4 algorithms are not included. Results labeled independent checks are only for small finite instances.

---

# VERITAS-ETH v1.4.0 — End-to-end exact weighted Cauchy / Hermite reconstruction

**Full cumulative source package; all v1.1 features retained.** Adds exact 2-adically weighted coefficient-wise rank-one modes, certified removal of entire modes whose contribution vanishes modulo `2**p`, and an explicit conventional recursion that constructs polynomial-valued child tensors with boundary variables. Every result is exact within supplied budgets. **This is not the manuscript D.4.4 weighted-mode packing construction or claimed subexponential algorithm.**

```sh
python -m pip install -e '.[test]'
python -m pytest -q
PYTHONPATH=src python -m veritas.cli cnf examples/example.cnf --weighted-children --packet-size 2 --node 1 --jet-order 4 --precision-bits 12
PYTHONPATH=src python scripts/validate_v12.py
```

API: `POST /v1/research/weighted-children`; choose **Weighted grouped modes + recursive child tensors** in the local web console. Full math, limits, verification scopes and regression requirements: [v1.2 technical notes](docs/WEIGHTED_CHILD_TENSORS_V12.md).

# VERITAS-ETH v1.1.0 — Exact Cauchy polynomial elimination + bounded packet optimization

**Full upgraded ZIP, retaining all v1.0 features.** This version adds exact polynomial-valued variable elimination for Cauchy jets and deterministic finite packet-collision optimization, with independent small-instance comparisons. The product is a bounded mathematical reasoning and tensor-network research implementation. It is **not** the manuscript's subexponential algorithm.

### What is new in v1.1

- Exact Cauchy-jet **polynomial factor elimination** over `(Z/2^p Z)[z]/z^K`, instead of always enumerating all `4^M` half-wire assignments. This is a different exact contraction algorithm with exponential worst-case treewidth dependence, **not** the manuscript's subexponential recursion.
- Reproducible finite packet optimization minimizing a clearly specified same-factor incidence collision score (exhaustive optimum for <=8 wires when full search completes, deterministic local swaps otherwise). This **is not the paper's collision-packing lemma**.
- Independent Cauchy-jet oracle comparisons, packet relabeling preservation checks, explicit resource caps and `UNKNOWN` behavior, CLI flags, API endpoints, browser operations, docs and deterministic validations.
- See [v1.1 technical audit](docs/PACKET_CAUCHY_ELIMINATION_V11.md), [scope ledger](docs/IMPLEMENTATION_STATUS.md), and [release notes](RELEASE_NOTES.md).

**Run the new bounded methods:**

```sh
PYTHONPATH=src python -m veritas.cli cnf examples/example.cnf --packet-schedule
PYTHONPATH=src python -m veritas.cli cnf examples/example.cnf --cauchy-eliminate --packet-size 2 --node 1 --jet-order 4 --precision-bits 12
PYTHONPATH=src python scripts/validate_v11.py
```

### Previous v1.0 features

- `src/veritas/research/recursive_separator.py`: balanced deterministic factor bipartition minimizing crossing wires, exact sum over separator edge assignments, recursive child contraction, collision diagnostics, optional residue arithmetic, resource caps and fail-closed behavior.
- `src/veritas/research/grouped_cauchy.py`: group row/column slots to preserve every nonzero node-matched interaction, decompose each cross-group Taylor coefficient matrix over rational numbers into rank-one modes, reconstruct exact entries, and independently validate local Cauchy jets.
- `POST /v1/research/separator-contract` and `POST /v1/research/grouped-cauchy`, CLI flags `--separator-contract`, `--cauchy-grouped`, `--group-span`, and interactive browser operations.
- Randomized tests, `scripts/validate_v10.py`, and a comparative small-instance benchmark `benchmarks/v10_separator.py`.

**Verification limits:** `RESEARCH_CROSS_CHECKED` means an independent finite-instance oracle agreed, **not a proof of a complexity theorem**. The code still does not implement the source D.4.4 collision-packing/mode-weight bound, specialized child network generation, or the full tapered D.5 reconstruction. Neither this code nor the manuscript's Lean proof has been independently compiled as part of this release. The conventional recursion and half-edge Cauchy evaluator have exponential worst-case costs.

See [`docs/SEPARATOR_GROUPED_MODES_V10.md`](docs/SEPARATOR_GROUPED_MODES_V10.md) for the exact identities, implementation scope and API examples.

### Quick start

Windows PowerShell: `./start_windows.ps1`; Linux/WSL/macOS: `./start.sh`. Or install `python -m pip install -e '.[test]'`, run `python -m pytest`, then `veritas-api`. Open <http://127.0.0.1:8080>. **Local-only:** there is no authentication or worker isolation for Internet deployment.

### CLI examples

```
veritas-cli cnf examples/example.cnf --separator-contract
veritas-cli cnf examples/example.cnf --cauchy-grouped --packet-size 2 --node 1 --group-span 1 --jet-order 5 --precision-bits 10
python scripts/validate_v10.py
```

---

# VERITAS-ETH v0.9.0 — Cauchy modes, modular Hermite + verified symbolic reasoning

**Full upgraded source ZIP.** v0.9.0 adds bounded valuation-certified cross-group Cauchy mode expansion and guarded finite-ring Hermite recovery. v0.8.0 reproduces the **exact local Cauchy kernel and its deformation equation (76)–(77)** from the manuscript for *tiny* CNF-derived bipartite tensor networks, using rational coefficients and shifted 2-adic jets. This remains an exhaustive mathematical reference, **not the full ETH contraction algorithm**. v0.7.0 added a separate exact split-wire testbed; both remain available. The inherited v0.6.0 release added independently verified **bounded exact #SAT counting certificates**, a **polynomial-semiring tensor contraction** returning the complete clause-violation histogram, safe exact arithmetic modulo powers of two, and **exact reconstruction of H(0)** from integer evaluations at nonzero nodes. Earlier SAT, exact counting, checked UNSAT, projected #SAT, equivalence, APIs, CLI, UI, tests and audit features remain.

**Scope:** This is NOT a complete implementation of the OpenAI paper's subexponential ETH algorithm, nor an independent Lean proof rebuild. The local Cauchy kernel is source-derived, but the original quantitative collision-packing, D.4.4 low-rank valuation modes, recursive child networks, and full D.5 recovery schedule are not implemented. Every provided contraction still has **exponential worst-case complexity**. No practical SAT performance breakthrough is claimed.

## Quick start

Python 3.10+ recommended. On Windows, extract ZIP and run from PowerShell:

```powershell
.\start_windows.ps1
```

On Linux/macOS/WSL:

```bash
./start.sh
```

Or install manually:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
python -m pip install -e '.[test]'
python -m pytest
python scripts/smoke.py
veritas-api
```

Open `http://127.0.0.1:8080` for the local console and `/docs` for API schemas. Avoid public network exposure: there is no remote authentication, sandbox, per-tenant quotas or hard process isolation.

## Added in v1.4.0 — complete bounded Cauchy-jet → exact-count recovery

- **Full end-to-end integration:** compute all nonzero-node Cauchy jets using the v1.2 grouped weighted rank-one mode + recursive child-tensor backend; combine them with exact rational Hermite recovery, including computed 2-adic guard precision.
- **Count semantics:** omitted precision chooses `n+1` bits to recover the exact integer #SAT; explicit smaller precision gives a residue, not an invented exact count.
- **Independent replay:** each local jet is checked by a separate exhaustive shifted-Cauchy evaluator and the reconstructed count by original undeformed tensor contraction (when `cross_check=true`). The result includes a replayable transcript digest and exact interpolation weights.
- **Global resource controls:** shared work/deadline budgets across all nodes, `UNKNOWN` on exhausted budgets; API `POST /v1/research/weighted-recovery`, CLI flag `--weighted-recovery`, browser selection and differential testing.
- **Limit:** exponential worst-case. This does NOT implement the manuscript's D.4.4 packing/weighted-mode complexity result or D.5 tapered Hermite strategy. See `docs/WEIGHTED_RECOVERY_V13.md`.

## Added in v0.9.0 — valuation-certified modes and modular recovery

1. **Precision-certified local cross modes:** explicitly expand the Cauchy kernel's cross-group interactions at a grid node, with exact 2-adic and `z`-adic lower bounds for safe branch elimination. This uses single-slot node-matching groups, **not** the manuscript's collision-packed low-rank modes.
2. **Finite-ring Hermite recovery:** compute exact rational constant-recovery coefficients and guard bits sufficient for modular jet interpolation, using only invertible odd denominators. Reject insufficient input precision.
3. **Independent differential checks:** compare mode-expanded local jets to the independent full-factor local evaluator; compare reconstructed `F(0)` residues to an independently contracted original tensor network.
4. **Integration:** new `/v1/research/cauchy-modes` and `/v1/research/cauchy-hermite` endpoints, CLI flags `--cauchy-modes`/`--cauchy-hermite`, UI choices, bounded tests, seeded validation.

Read **`docs/MODES_HERMITE_V09.md`** for the mathematical identities, proof boundary and exact API examples. The full D.4.4 grouped mode factoring, collision packing, recursive child tensors and subexponential algorithm **remain unimplemented**.

## Added in v0.8.0 — source-derived mathematical construction

1. **Actual manuscript D.4.3 kernel:** exact rational `W_xy(T) = C(T)/(C'(0)(T-(y-x)))`, using packet sizes `1, 2, 4, 8` and full degree `2L-1`. Each entry is a polynomial by exact factor cancellation. Source formulas (76)–(77), not the prior toy split-wire kernel.
2. **Bounded exact Cauchy deformation:** compute the network polynomial `F(T)` by exhaustive `4**M` half-edge enumeration; verify `F(0)` against an independent tensor contraction and every special node `t in [-L,L-1]` against a separate direct evaluation.
3. **Correct 2-adic local coordinates:** for `alpha=2L`, calculate `W(t+alpha*z)` with *2-adically integral* rational coefficients; odd-denominator fractions are inverted exactly modulo `2**p`. Compute truncated modular jets independently and cross-check against shifting the full rational polynomial.
4. **API, CLI, console and regression tests:** `POST /v1/research/cauchy-deformation`; `veritas-cli cnf FILE --cauchy-deformation --packet-size 2 --node 0 --jet-order 4`; UI dropdown, source-linked audit status, strict input limits, and seeded randomized comparisons. Full details: `docs/CAUCHY_DEFORMATION.md`.

**Not done:** paper-specific packet collision packing, valuation-weighted interaction-mode decomposition, recursive factorization and polynomial-space runtime. This is **not** an ETH-solving or LLM-inference breakthrough. No Lean theorem is claimed reproduced.

## Added in v0.7.0

1. **Research split-wire deformation**: every tensor-network wire is replaced with two half-edges coupled by `K_T(a,b) = 1` for matching bits and `T` for mismatched bits. The degree-`E` polynomial satisfies `D(0)=original contraction`, `D(1)=product of unsigned local sums` and `D(-1)=product of signed local sums`. See `docs/WIRE_DEFORMATION.md`.
2. **Independent checks**: generic polynomial bucket elimination and a separate exhaustive half-edge histogram, plus independent CNF assignment enumeration and two rank-one identities. Tested with signed tensors, contradictions, no edges, repeated literals, empty clauses, and optional exact modular coefficients.
3. **New API, UI and CLI**: `POST /v1/research/wire-deformation`, web console dropdown, and `veritas-cli cnf examples/example.cnf --wire-deformation [--precision-bits 4]`.
4. **Performance guardrails**: hard edge/table/time limits, deterministic min-fill ordering, all integer arithmetic and result/provenance hashing. Nothing uses neural inference or proves a faster runtime bound.

The end-to-end seed validation compares 250 exact histograms and 750 modular coefficient sets. See `validation/validation_v07.json`.

## Added in v0.6.0

1. **Proof-carrying #SAT**: `POST /v1/certify/count` builds a bounded complete Shannon tree; `/v1/certificates/check-count` independently checks that every assignment is counted exactly once. `COUNT_PROOF_CHECKED` certifies the arithmetic for the submitted original CNF, not algorithmic speed.
2. **Exact clause-violation spectrum**: `POST /v1/research/violation-spectrum` computes every coefficient of `H(T)=sum_x T^(number of violated clauses)`, using polynomial-valued tensor bucket elimination. `H(0)` is #SAT, `H(1)=2^n`, and the lowest nonzero degree provides the small-instance Max-SAT optimum.
3. **Certified modular arithmetic and interpolation identities**: optional `precision_bits` performs exact computations in `Z/(2^p)`, retaining only terms nonzero modulo `2^p`. Values at nodes 1 through m+1 reconstruct H(0) by integer finite differences. Insufficient precision yields residues only, never an invented exact count.
4. **CLI/UI/testing**: `veritas-cli cnf FILE --certify-count`, `veritas-cli check-count FILE.cnf proof.json`, `veritas-cli cnf FILE --spectrum [--precision-bits 4]`; differential tests and release validation. See `docs/MODES_HERMITE_V09.md`, `docs/CAUCHY_DEFORMATION.md`, `docs/WIRE_DEFORMATION.md`, `docs/COUNTING_PROOF_FORMAT.md` and `docs/POLYNOMIAL_RESEARCH.md`.

## Inherited features (v0.5.0)

1. **Independent bounded UNSAT refutation checker.** `POST /v1/certify/unsat` generates a complete split/unit/conflict DPLL-tree certificate. `POST /v1/certificates/check` independently validates its completeness and clause contradictions. Successful checks have `PROOF_CHECKED` status. A `max_nodes`/time/bytes limit fails closed to `UNKNOWN`, not a bogus proof. These are potentially exponentially large, **not** industrial LRAT/DRAT proofs.
2. **Optional checked verification and entailment.** `/v1/verify` and `/v1/counterexample` accept `request_unsat_certificate: true`. Their default no-certificate UNSAT status remains `SOLVER_ONLY` for backward compatibility.
3. **Formula equivalence.** `POST /v1/equivalent` parses two explicit propositional formulas and returns `EQUIVALENT` or a counterexample independently evaluated against both original expressions. Optional checked UNSAT proof for equivalent formulas.
4. **Exact projected counting.** `POST /v1/count/projected` counts unique valuations of the given variables having at least one satisfying extension over all other variables. Implemented through bounded model enumeration and blocking clauses, cross-checked by an independent exhaustive oracle for small instances. Maximum 12 projected variables (not necessarily 12 total declared variables). No weighted/projected certificate is claimed.
5. **CLI and UI integration.** Console includes equivalence, projected counts and certificate generation. `veritas-cli cnf FILE --certify-unsat`, `--project 1 2`, and `veritas-cli check-proof FILE.cnf proof.json` are supported. `check-proof` exits nonzero for a rejected proof.

## API examples

```bash
curl -X POST http://127.0.0.1:8080/v1/certify/unsat -H 'Content-Type: application/json' -d '{"n":1,"clauses":[[1],[-1]]}'
curl -X POST http://127.0.0.1:8080/v1/count/projected -H 'Content-Type: application/json' -d '{"n":3,"clauses":[[1,2]],"projected":[1,2]}'
curl -X POST http://127.0.0.1:8080/v1/equivalent -H 'Content-Type: application/json' -d '{"left":"A -> B","right":"!A | B","request_unsat_certificate":true}'
```

New v0.8 route: `/v1/research/cauchy-deformation`. Additional v0.7 route: `/v1/research/wire-deformation`. v0.6 routes: `/v1/certify/count`, `/v1/certificates/check-count`, `/v1/research/violation-spectrum`. Inherited routes: `/v1/formalize`, `/v1/verify`, `/v1/count`, `/v1/counterexample`, `/v1/research/contract`, `/v1/paper/audit`, `/v1/audits/{sha256}`, `/health`. A local SHA-256 hash chain records results but is not tamper-proof against host administrators. Input formulas are formal propositional syntax, **not arbitrary English**.

### Evidence distinctions

- `WITNESS_CHECKED`: independent evaluation of a complete satisfying assignment.
- `PROOF_CHECKED`: DPLL-tree UNSAT certificate structurally checked against original CNF; bounded, independent of generator's search logic.
- `SOLVER_ONLY`: UNSAT result without checked proof.
- `COUNT_PROOF_CHECKED`: a complete bounded exact-counting tree was independently checked against the original CNF.
- `CROSS_CHECKED`: separate small-instance oracle agrees on an exact count.
- `EXACT_ALGORITHM`: completed exact algorithm without an independently checked counting certificate.
- `RESEARCH_ONLY`: toy/experimental mathematical computation that does not imply production reliability.
- `UNKNOWN`: resource budget exhausted; no conclusion/count must be inferred.

## Test, integrity and research status

```bash
python -m pytest
python scripts/validate_10000.py
python scripts/validate_upgrade.py
python scripts/smoke.py
python scripts/validate_v06.py
python scripts/validate_v07.py
python scripts/validate_v08.py
python scripts/validate_v09.py
python scripts/verify_manifest.py
```

See `docs/MODES_HERMITE_V09.md`, `docs/CAUCHY_DEFORMATION.md`, `docs/WIRE_DEFORMATION.md`, `docs/COUNTING_PROOF_FORMAT.md`, `docs/POLYNOMIAL_RESEARCH.md`, `RELEASE_NOTES.md`, `docs/IMPLEMENTATION_STATUS.md`, `docs/PAPER_TO_CODE_MAP.md`, `docs/SECURITY.md` and `docs/FULL_IMPLEMENTATION_PLAN.md` for coverage and known gaps. The Lean helper script does not itself establish the manuscript's theorem, and OpenAI's Lean statement should be distinguished from the sharper paper bound.

Upstream background: [OpenAI Lean scope](https://github.com/openai/math/blob/main/lean/docs/378.md), [PySAT](https://pysathq.github.io/), [Ganak](https://github.com/meelgroup/ganak), [Z3](https://github.com/Z3Prover/z3). External binaries are optional and not shipped with this archive.


## v1.4 — parsimonious bounded-degree tensor conversion

The new `bounded_degree_from_cnf` encoder replaces a variable's large equality
factor with an acyclic chain of at most ternary COPY tensors. A Boolean value
propagates uniquely through the gadget; isolated original variables contribute
2 rather than disappearing. The number of tensor wires rises from the number
of literal occurrences `L` to at most `L + sum(max(occurrences(v)-3,0))`.
The maximum variable-gadget factor degree is **3** (clause width is still
bounded separately). This enables exact tensorization of high-occurrence CNFs
without exponential-size variable equality tables. The reduction is
parsimonious; it is not the counting-preserving sparsification theorem in the
ETH manuscript and it does not make general contraction subexponential.

Use `python -m veritas.cli cnf examples/example.cnf --bounded-degree` for
construction statistics. Add `--gadget-contract` to run the bounded exact
min-neighbor baseline. The browser UI provides two matching operations;
`POST /v1/research/bounded-degree-tensor` accepts `contract:true` and strict
resource limits. Exact counts on formulas with <=10 variables are checked
against a separate exhaustive Boolean oracle when requested via API.

Run `python -m pytest -q`, `python scripts/validate_v14.py`, and
`python scripts/verify_manifest.py` after packaging.

## v2.6 — exact finite Appendix D.3 conditional-expectation packing

This release introduces a new, isolated research module for the manuscript's **actual directed pair-label squared-collision potential**, unlike the earlier endpoint-load surrogate. It uses distinct vertex-symbol variables for the row/column sides, deterministic exact conditional-expectation choices, common-H padding of **all** directed classes, orientation-aligned packet positions, and an independent certificate checker.

CLI example (from installed project):

```bash
veritas-eth26 pack --edges-json '[[0,1],[1,0],[0,0],[1,1]]' --r 2 --a 1 --output d3.json
veritas-eth26 check --certificate d3.json
veritas-eth26 parameters --s 1000
```

Local API: `POST /v1/research/eth/d3/construct`, `POST /v1/research/eth/d3/check`, and `GET /v1/research/eth/d3/status`. The new UI section runs the constructor. The full JSON certificate is returned by the API and CLI.

**Scope limitation:** This is a bounded **finite D.3 implementation** with checked instances; no D.4.4 weighted-mode subexponential recursion has been implemented. `u_d` now uses the manuscript's ceiling formula; v2.5 mistakenly used floor. See `docs/ETH_V26_D3_MATHEMATICAL_SCOPE.md`.


## v3.1 finite geometric Taylor-mode children

The `veritas-eth31` command and `/v1/research/eth/geometric-mode-children` route compute bounded exact D.3-driven geometric cross-mode expansions with group-local scalar child factorization, checked against direct half-edge enumeration. See `docs/GEOMETRIC_JET_MODE_CHILDREN_V31.md`. This does not implement the manuscript's subexponential recursion.

### R0/R1 exact-foundation development

The bounded quotient-ring API and independently evaluated CNF/tensor checks
are documented in [R1 exact foundation](docs/R1_EXACT_FOUNDATION.md).
The source lock, open function-level audit, and unqualified theorem obligations
are explicit there. These finite checks do not establish the recursive theorem
or its complexity bound.

The [source-shaped CNF recursion bridge](docs/SOURCE_CNF_RECURSION.md) now
checks the finite equality-tree reduction and can compare active point-child
sums with a direct half-edge oracle. Its nonshrinking finite fallback is
explicit; the manuscript theorem branch remains unimplemented.

The current finite child-recipe, per-tuple identity and source-Hermite repairs,
including their limits, are documented in
[mathematical repair progress](docs/MATHEMATICAL_REPAIR_PROGRESS.md).

The [R8.1 tuple-stream check](docs/TUPLE_STREAM_R81.md) independently counts
and verifies the finite structural tuple domain, rejects substitution and
reordering, and enables direct point checks by default for very small active
calls. The theorem branch remains disabled.

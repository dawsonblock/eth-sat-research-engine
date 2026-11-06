# v3.6.0 — exact finite packet tensor coefficients

- Original v3.5 code retained.
- Boolean-multilinear packet-level polynomial coefficient extraction in an exact truncated 2-adic extension jet ring.
- Independent coefficient verification using direct evaluations plus Möbius inversion.
- Global exact packet contraction checked against independent direct half-edge enumeration.
- Replayable fail-closed certificates, resource caps, browser/API/CLI integration.
- Not the D.4.4 shrinking recursive packet tensor construction; no M/8 or subexponential complexity claim.

v3.4.0: Structural D.3 port/mode ledger + checked v3.3 finite contraction bridge. See RELEASE_NOTES_V34.md. No M/8 child wire or ETH theorem proof.

# v2.6.0 — finite Appendix D.3 conditional expectation and independent verification

See `RELEASE_NOTES_V26.md` and `RELEASE_REPORT_V26.md`. This release adds exact directed pair-label derandomization, complete common-H packet padding and independent finite certificate replay. It also corrects the manuscript parameter-ceiling and numeric D.6 eligibility handling. The D.4.4 subexponential recursion is **not** implemented.

# v2.5.0

See `RELEASE_NOTES_V25.md` for new exact-reference and packet-checking modules; prior versions retained.

# Current release: v2.4.0

See `RELEASE_NOTES_V24.md` for exact all-variable posterior marginals, verification, tests and limitations.

---

# Current release: v2.3.0

See `RELEASE_NOTES_V23.md` for the full v2.3 upgrade, rational counting semantics, validation evidence and known limits.

---

# VERITAS-ETH v2.2.0

Exact component-DAG #SAT certificates with factor decomposition, memoization,
replay checker, and API/CLI/browser integration. Full previous functionality
retained. See `RELEASE_NOTES_V22.md` and `RELEASE_REPORT_V22.md`.

---

## v2.1.0

- Bounded finite packet branch-and-bound (sizes 1/2/4/8) with admissible bounds.
- Independent objective/bound replay and small DP differential checks.
- API, CLI and browser integration, evidence downgrade on budget cutoff.
- No claimed subexponential #SAT algorithm.

# v2.0.0

- Added exact global minimum-weight perfect matching for the finite 2-wire packet collision objective.
- Odd wire counts supported using a zero-weight dummy vertex.
- Independent direct factor-incidence replay; small instances cross-check exact subset DP.
- Added optional NetworkX dependency, API/CLI/UI/Cauchy integration, seeded tests, and benchmark.
- Conservatively labelled external optimum reliance versus small-instance independent certification.
- Retains the complete v1.9.0 cumulative codebase.
- Manuscript D.3/D.4.4 and subexponential ETH solver are NOT implemented.

---

# v1.9.0 — Scalable packet lower-bound certificates

- New `research/scalable_packets.py`: deterministic seeded multistart search,
  incremental cross-packet swap evaluations, candidate budgets and valid
  incumbent on timeout.
- Derives global lower bounds for the **finite surrogate collision score**.
  Labels a result globally optimal only when both bounds are attained.
- New independent `research/packet_bound_checker.py` rejects mismatched
  permutations, scores and false optimality claims without invoking optimizer.
- Integrated into API (`optimizer=scalable`), CLI (`--scalable-packets`),
  browser console, and bounded polynomial Cauchy elimination.
- Added v1.9 independent permutation-oracle tests, forged-evidence tests,
  large-network validation and planner-only benchmark.
- Limits: unlike v1.8 exact DP, v1.9 search is heuristic if the lower bound
  is not attained. Still not manuscript D.3 or subexponential ETH algorithm.

---

# v1.8.0 — Finite exact packet partition DP

- Globally optimal lexicographic packet incidence score for <=16 wires by partition subset DP (within explicit budgets); previously exact optimum used factorial exhaustive permutations only up to 8 wires.
- Independent score replay, count-preserving wire-relabeling regression, safe resource failures.
- Optional exact packet optimizer for Cauchy polynomial elimination; API, CLI, browser UI and added tests and benchmarks.
- Not the paper-specific D.3/D.4.4 packing construction. No new asymptotic runtime claim.

---

# v1.7.0 — Globally optimal finite-graph ordering (October 30, 2026)

- Implemented exact subset-DP for minimum dense-work elimination order on <=12
  original CNF variables, with separate minimum-width constrained-work mode.
- New independently replayed graph-fill and certified decomposition invariants.
- Added opt-in `optimal_small` adaptive planner (no silent fallback), plan-only
  CLI/API, UI option and full differential validation suite.
- Fixed finite benchmark: 222 -> 190 estimated operations and width 5 -> 4;
  planning overhead makes tiny-instance wall-clock **worse**, not better.
- No ETH theorem reproduction or runtime speedup claim. See
  `RELEASE_REPORT_V17.md` and `docs/EXACT_ORDER_OPTIMIZATION_V17.md`.

---

# v1.6.0 exact contraction optimization

Indexed bit-projection executor, separately selectable exact sparse hash-join backend, quick min-degree planner fallback, API and CLI controls, comparative validation and benchmark. No proof of ETH runtime or unconditional speedup is claimed. See `docs/FAST_SPARSE_CONTRACTION_V16.md` and `validation/benchmark_v16.json`.

---

# v1.5.0 — Adaptive exact contraction (2026-10-30)

- Added `graph_decomposition.py`: primal interaction graphs, connected components, deterministic small separator search, elimination-tree construction and decomposition validation.
- Added `contraction_planner.py`: original CNF factorization including duplicates/tautologies/free variables; v1.4 COPY3 network comparison; true min-fill, min-degree and weighted-fill planning; exact dense integer/modular execution under explicit caps.
- Added `boundary_dp.py`: exact separator conditioning, component-product decomposition, canonical-factor memoization, memory-budget index slicing, independent shared work and deadline limits.
- Added `adaptive_contract.py`: planner-selected arithmetic and structural execution with direct JSON diagnostics. No partial counts returned on cap exhaustion.
- Added `/v1/research/adaptive-contract`, CLI `--adaptive-contract`, browser option, regression tests and seeded 500-instance/4500-comparison validation.
- Updated all API health-version tests from v1.4.0 to v1.5.0. Inherited v1.4 APIs are preserved.
- Benchmark disclosure: v1.5 reduced factor-evaluation counts on four structured cases but had slower observed wall-clock time than v1.4 because of planning overhead. No speedup guarantee.

**NOT IMPLEMENTED:** Paper's full D.3 packing, D.4.4 quantitative weighted modes, ETH-specialized subexponential recursive contraction, external Lean proof rebuild, process-level hard memory caps, sparse factor representations or third-party planner integrations.

---

# VERITAS-ETH v1.4.0 — verified bounded-degree tensor upgrade

New exact parsimonious COPY3 equality-gadget encoder removes exponential
high-occurrence variable tensors. Added deterministic exact min-neighbor
contraction with explicit budgets, API/CLI/browser integration, 226 tests,
800 seeded independent differential cases and unchanged 10,000-case
SAT/#SAT regression. Full implementation details:
`docs/BOUNDED_DEGREE_V14.md`, `RELEASE_NOTES_V14.md`.

This implementation is NOT the paper's D.4.4 collision packing or its
subexponential algorithm. No ETH runtime or formal Lean theorem is claimed.

---

# v1.3.0 — End-to-end weighted child-tensor count recovery

## New implementation

1. Guarded full multi-node Hermite reconstruction of `F(0)` from the existing v1.2 exact weighted Cauchy child-tensor jets.
2. Exact integer #SAT output when `target_bits >= declared_variables + 1`; otherwise the response is explicitly a modular residue.
3. Shared wall-clock and work budgets over all nodes; resource exhaustion fails closed to UNKNOWN.
4. Independent shifted-Cauchy jet checks and undeformed original tensor contract checks; replayable SHA-256-bound interpolation transcript (not a succinct proof).
5. Endpoint, CLI, browser interface, seeded differential tests and mathematical documentation.

## Nonclaims

Worst-case runtime is exponential. Full D.4.4 collision packing, asymptotic mode-count bounds, D.5 tapered schedule, and Lean proof reproduction are not implemented. All source v1.2 functionality is inherited.

# v1.2.0 — Exact weighted Cauchy modes and recursive child boundary tensors

- Full cumulative upgrade of v1.1.0.
- Exact rational coefficient rank-one modes, each annotated with a 2-adic lower bound. Modes are omitted only when every entry vanishes modulo the chosen power of two; final matrix is checked coefficient by coefficient.
- General half-edge polynomial factor network and explicit balanced recursive boundary-tensor construction over `(Z/2^p Z)[z]/(z^q)`, with degree/valuation-safe zero short-circuits.
- API, CLI, local browser UI, test suite, differential validation, resource limit behavior, and algorithm-scope ledger.
- **No manuscript D.4.4 asymptotic collision-packing/mode bound or subexponential solver**. Worst-case complexity remains exponential.

---

# VERITAS-ETH v1.1.0 — Finite packet optimization and modular polynomial elimination

**Release type:** working bounded mathematical research implementation. **ETH paper reproduction remains incomplete.**

## Added
- `research/packet_schedule.py`: exact finite collision-score optimizer for <=8 wires if full enumeration completes, deterministic local swaps for 9..16 wires; port-table-preserving wire permutation.
- `research/cauchy_elimination.py`: exact polynomial sum-product factor elimination of shifted Cauchy jets in `(Z/2^p Z)[z]/(z^K)`, with exact arithmetic and bounded tables.
- API `/v1/research/packet-schedule`, `/v1/research/cauchy-eliminate`; CLI flags and browser selections; independently cross-checked reference results.
- New randomized and adversarial tests, deterministic validation script, toy benchmark, revised status and implementation ledger.

## Accuracy and limitations
- Input is restricted to a finite small number of edges. Some calculations are exponential in induced factor width.
- Optimizing *incidence collisions* is a diagnostic heuristic, not the manuscript D.3 collision-packing construction or proof.
- No implementation of D.4.4's weighted low-rank child-tensor factorization or its specialized subexponential recursive contraction.
- No implementation of the full finite-ring tapered precision schedule. Lean formalization has not been rebuilt in this release.
- The only new trusted claims are exact small-instance identities with independent reference cross-checks.

## Validation
See `validation/validation_v11.json` and the current release summary. Other validation files are historical records reproduced from the v1.0 baseline; they are not new work in v1.1.

---

# VERITAS-ETH v1.0.0 — exact recursive factor separators and grouped Cauchy coefficient modes

## Implemented

- Added exact recursive factor-separator contraction with exhaustive balanced partition optimizer. Tracks cut width, repeated cut incidences, branch/leaf counts and cache statistics. Fails closed on resource limits; modulus arithmetic is exact.
- Added coefficient-wise rational rank-one cross-group Cauchy mode decomposition, exact recomposition, and oracle comparison with independently generated shifted local jets.
- Added API, CLI and local browser access, 10 new automated tests, standalone seeded v1.0 validation, a smoke benchmark, updated scope ledgers and developer instructions.
- All v0.9.0 SAT / #SAT / independently checked proof / 2-adic / Cauchy / Hermite features remain included.

## Evidence

See `validation/release_summary.json` and `validation/validation_v10.json`. Randomized differential checks are finite-instance correctness evidence only, **not** proof of faster asymptotic complexity.

## Deliberately not claimed

**No** source D.4.4 quantitative packet collision-packing implementation, source-specific weighted symbol-group tensor modes, low-wire child-network identity, source D.5 tapered Hermite precision schedule, end-to-end subexponential ETH algorithm or independent Lean build. The new recursion is generic and exponential worst-case, and the rank-one decomposition still uses exhaustive Cauchy half-edge enumeration.

Complete mathematical description: `docs/SEPARATOR_GROUPED_MODES_V10.md`.

---

# VERITAS-ETH v0.9.0 — finite-ring recovery and certified local modes

## Implemented and independently tested

- `research/cauchy_modes.py`: deterministic grouping by matched row/column slots at the Cauchy grid node; exact expansion of affine row factors into local and cross-group terms. Each pruned branch has a certified lower bound proving zero modulo `2^p` or modulo `z^q`. Fully evaluates small instances by exponential half-edge enumeration; **not** the paper's D.4.4 group/packing/mode-count algorithm.
- `research/hermite_ring.py`: rational confluent Vandermonde solver; explicit 2-adic inverse-weight guard-bit calculation; precision-safe modular constant reconstruction from nonzero-node jets. Rejects insufficient precision or invalid residue data. **Not** the entire D.5 recovery schedule.
- New API routes, CLI flags, UI operations, tests, engineering documentation and seeded v0.9 validation.
- Full backward-compatible v0.8 baseline with inherited SAT, exact counting, independent bounded UNSAT and count certificates, projected counting, formula equivalence, Cauchy local kernels and tensor research.

## Release evidence

- Full pytest suite passing (see `validation/release_summary.json`).
- `scripts/validate_v09.py` reports **213** independent mode/full-jet checks and **95** Hermite/original-contraction checks, along with 5285 valuation-certified and 720 degree-certified pruned branch events. Counts are finite seeded checks, not formal theorems.
- Inherited validators remain passing. Run `python scripts/verify_manifest.py` to verify the released file contents.

## Not implemented / deliberately not claimed

- Original collision-packing schedule and its combinatorial bounds.
- Manuscript D.4.4 low-rank symbol-group interaction modes and recursive child-tensor identity.
- End-to-end subexponential contraction or formal proof of its runtime.
- Full tapered D.5 precision/recovery schedule or independent compilation of upstream Lean.
- Network-facing production hardening (authorization, isolation, quotas, durable cancellation).

Read `docs/MODES_HERMITE_V09.md` for the mathematical and experimental scope.

---

# VERITAS-ETH v0.8.0 — complete upgraded source release

## New, tested code

- Added source-derived Appendix D.4.3 **Cauchy polynomial kernel** of formula (76), using exact rational coefficients, and the small bipartite tensor polynomial of formula (77).
- Added **special-node direct checks**, `F(0)` equivalence to original tensor count, explicit degree bounds and exact packet-grid shift sparsity checks.
- Added **2-adically integral local coordinate jets**: odd denominators are units modulo `2**p`; exact modular residues are compared to an independently shifted full rational polynomial.
- Added API endpoint, command-line flags, browser option, tests, seeded validation, source mapping, new `docs/CAUCHY_DEFORMATION.md`.
- Preserved all v0.7.0 SAT, #SAT, certified-count, certificate checking, projected counting, split-wire and violation-spectrum functionality.

## Nonclaims and remaining tasks

This reference performs explicit `4**M` half-edge enumeration and accepts at most six original wires. It implements neither the **collision-packing and tapered finite-ring Hermite recovery** nor the **valuation-weighted mode factorization, recursive child-network construction, space/time complexity proof, or complete Lean theorem reproduction**. The original paper's subexponential time bound **does not apply to this implementation**.

## Source

- https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-reduction.tex
- https://github.com/openai/math/blob/main/lean/docs/378.md
- See `docs/CAUCHY_DEFORMATION.md`, `docs/IMPLEMENTATION_STATUS.md`, and machine-generated validation files for precise provenance and constraints.

---

# VERITAS-ETH v0.7.0 — full upgraded release

## New in v0.7.0 (executed and verified locally)

- Exact *toy split-wire* deformation: `K_T(a,b)=1` when the endpoint bits agree and `T` otherwise; a polynomial of degree at most the number of wires. The constant coefficient is the original tensor contraction.
- Exact generic polynomial-semiring bucket contraction using a deterministic min-fill edge order; no floating-point approximation.
- Independent half-edge exhaustive histogram oracle, plus independent factorized-node checks at `T=+1,-1` and original #SAT checks when feasible.
- Support for integer coefficients or exact residues modulo `2**p` with explicit residue semantics.
- New API `/v1/research/wire-deformation`, command-line `--wire-deformation` and local console dropdown; bounded failure handling.
- Tests: all inherited automated cases plus new API, signed-tensor, metamorphic and adversarial cases. Standalone seeded validation performs 250 full half-edge histogram comparisons and 750 modular coefficient comparisons.
- Clean release archive excluding mutable `.veritas` local audit state. Manifest checks every included release file.

## Scope disclosure

This release **does not implement** the OpenAI paper's Cauchy low-degree wire deformation, valuation-based mode pruning, or subexponential recursion. New research uses a degree-E split-wire deformation and conventional exponential-time tensor elimination; no performance theorem follows. The Lean proofs have not been independently compiled as part of this release. No industrial proof or publicly deployed service is claimed.

## v0.6.0 (inherited)

# VERITAS-ETH v0.6.0 — full upgraded source release

## Validated changes from v0.5.0

- **Full bounded exact #SAT proof checking**: generator and independent checker for a complete unit/split/contradiction/satisfied Shannon counting tree. Every original clause and declared Boolean variable is accounted for; a checked certificate proves the exact count for its pinned CNF. Supports UNUSED variables and empty clauses, strict time/node/byte limits, adversarial mutation tests and UNKNOWN when over budget.
- **Violation-count polynomial tensor contraction**: computes `H(T)=sum_x T^violated(x)` through a polynomial-valued factor network, using generic bucket elimination over exact integer coefficients. The degree-0 coefficient is #SAT; the smallest nonzero degree gives the Max-SAT optimum.
- **Exact 2-adic quotient-ring evaluation**: optionally computes all polynomial coefficients modulo `2^p`, provably omitting only products divisible by `2^p`—not approximate pruning. When `p > n`, residues uniquely recover every coefficient; otherwise exact counts are not reported.
- **Integer interpolation verification**: recovers H(0) using H(1)..H(m+1) with integer finite-difference weights and cross-checks its constant coefficient. This is a small exact algebra identity, not Cauchy wire deformation.
- **API, CLI, interactive UI and docs**: `/v1/certify/count`, `/v1/certificates/check-count`, `/v1/research/violation-spectrum`, CLI operations and browser selector options.
- **Release validation**: all inherited tests, new API/adversarial/property tests, standalone seeded 1,000 proof checker vs exhaustive count, 350 polynomial-vs-oracle cases and 1,400 modular-residue comparisons. See `validation/validation_v06.json` for the reproducible results.

## Strict limitations

- No reproduction of OpenAI's subexponential ETH algorithm, Cauchy wire-identification deformation, full recursive mode-pruning contraction, Lean theorem compilation, or a proof of paper runtime bounds.
- No industrial-sized exact #SAT certificate; counting trees have worst-case exponential size and a hard budget.
- No remote authentication or OS-enforced worker sandbox; localhost only.
- No claim of scalable Max-SAT or neural model performance improvements.

## Inherited v0.5.0

# VERITAS-ETH v0.5.0 — full upgraded source release

## Validated additions over v0.4.0

- Exact bounded UNSAT DPLL search-tree proof generation and a **separate strict checker**. Explicit unit derivation, both branches of every split, concrete falsified-clause leaves; no untrusted solver proof flags.
- SAT witness verification and optional PROOF_CHECKED evidence for `/v1/verify` and entailment.
- New `/v1/certify/unsat`, `/v1/certificates/check`, `/v1/count/projected`, `/v1/equivalent`.
- Projected count with exact distinct-solution blocking; independent small-domain projection oracle; strict resource-limited UNKNOWN semantics.
- UI and CLI upgrades; independent local proof-checking command; adversarial mutated-certificate regressions and randomized differential tests.
- Complete release manifest, staged validation outputs, and a clean reproducible source archive.

## Not implemented

- OpenAI's proposed subexponential ETH algorithm or its faithful recursive contraction.
- Original Cauchy polynomial deformation or all necessary quantitative bounds.
- Upstream Lean theorem compilation and detailed proof audit on a pinned revision.
- Independent LRAT/DRAT proof checking, polynomial-size counting certificates, or scalable projected counting.
- Safe Internet deployment, strong worker process isolation, or natural-language semantic verification.
- Pinned release testing of the optional Ganak executable.

All proof performance and differential data in `validation/` are limited to small generated examples, not evidence for ETH runtime asymptotics.

## v3.8.0 — exact group-local child elimination

Adds bounded exact fixed-beta D.4.4 child-factor contraction over the extension jet ring,
with connected-component decomposition, memoized packet table generation,
independent Cauchy oracle checks, source-replayed certificates, CLI/API/UI, and tests.
This is a finite reference optimization, **not** the manuscript's recursively
regenerated child tensor algorithm or a proof of subexponential SAT.
See `RELEASE_NOTES_V38.md` and `RELEASE_REPORT_V38.md`.

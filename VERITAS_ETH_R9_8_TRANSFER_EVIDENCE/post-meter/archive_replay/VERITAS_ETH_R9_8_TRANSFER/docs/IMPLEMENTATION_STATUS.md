## v3.0 (finite research only)

Implemented: D.3-based group assignment, lazy extension-ring Cauchy half-edge factors, implicit boundary-child tensors with memoization, direct half-edge and T=0 exact count oracles, replayable fail-closed certificates. **Not implemented:** manuscript D.4.4 geometric-tile weighted-mode child recursion, child size M/8 bound, subexponential complexity proof. See `IMPLICIT_EXTENSION_CHILDREN_V30.md`.

## v2.9.0 status (latest)

**Implemented (bounded exact reference):** node-dependent tapered Hermite schedule with mixed-precision rational recovery, known-polynomial replay; finite extension-ring Cauchy coefficient-jet rank-one cross-group modes with independent certificate reconstruction and 2-adic valuation checks. See `TAPERED_EXTENSION_MODES_V29.md` and `RELEASE_REPORT_V29.md`.

**Not implemented:** manuscript D.4.4 geometric tile-mode expansion in full extension-jet ring, specialized child tensors, complete subexponential recurrence, polynomial-space asymptotic proof. Underlying public manuscript commit not pinned. Other legacy status reports below describe inherited components only.

# v2.5 status update

M0 COMPLETE. M1a finite packet verification COMPLETE, M1b manuscript theorem
OPEN. M2a small extension-ring arithmetic COMPLETE, M2b full ring/interpolation
OPEN. M3a Cauchy polynomial identity COMPLETE, M3b recursive integration OPEN.
All D.4.4 asymptotic work remains OPEN.

# v2.3 current implementation status

- **Working bounded reference**: exact weighted model count, independent
  count-certificate checker, conditional probability with independent Bernoulli
  priors. All prior Boolean/tensor/Cauchy modules retained.
- **Not implemented**: manuscript D.3 collision-packing theorem and D.4.4
  subexponential recurrence, complete Lean reproduction.
- **Evidence**: `RELEASE_REPORT_V23.md`, `docs/WEIGHTED_COUNTING_V23.md`.

---

# v2.2 current implementation status

**New:** `solvers/count_dag.py` implements count-preserving exact component-DAG
proofs and replay verification, plus API/CLI/browser integration. New format
makes decomposable formulas substantially smaller but does not certify a
subexponential complexity bound. The verifier shares a deterministic local
reduction kernel with the generator; independent exhaustive-counting tests
provide small-instance corroboration. See `COMPONENT_COUNT_DAG_V22.md`.

**Still not implemented:** the original paper's D.3 collision-packing and
D.4.4 specialized weighted-mode recursive contraction.

---

# v2.0.0 added capabilities

- **Exact two-wire packet scheduling:** solved by min-weight perfect matching.
  Globally optimal for the **finite engineering incidence collision proxy**.
- **Certified status:** direct independent factor-incidence checker plus exact
  subset-DP cross-check on <=16 wires; large cases rely on external Blossom
  implementation, **not** an independently verified proof certificate.
- **Integrations:** API, CLI, browser and small Cauchy-jet optimizer.
- **Not achieved:** paper D.3 packing bounds, D.4.4 specialized recursion,
  subexponential SAT/#SAT runtime, general end-to-end solver speedups.

---

## v1.9.0 status (new)

**Implemented:** bounded multistart packet scheduling on networks up to 256
wires by default; provable finite per-factor lower bounds for pair collisions
and peak incidence; independent checker and conditional globally optimal
surrogate-score evidence; Cauchy scheduler option; API/CLI/UI; tests.

**Not implemented:** original D.3 quantitative collision packing, D.4.4
weighted-mode complexity theorem, an end-to-end subexponential algorithm,
or an independent formal Lean reproduction. The finite lower-bound claim is
only about v1.1 incidence collisions, not computation complexity.

---

# Latest: v1.8.0

**Implemented:** finite exact subset-DP packet-partition optimization for up to 16 wires, independent score replay, API/CLI/UI and optional modular Cauchy integration. Confirmed strictly improved surrogate collision score on a fixed 12-wire factor network (6 to 5). **Not implemented:** manuscript D.3 collision packing theorem, D.4.4 quantitative recursion or a subexponential SAT algorithm. This exact finite optimizer remains exponential in the number of wires. See `EXACT_PACKET_PARTITION_DP_V18.md`.

---

# Latest: v1.7.0

Added exact finite-graph subset dynamic programming for dense-work and width
objectives, independent replay, opt-in counting and plan-only API. The D.3/D.4.4
quantitative ETH subexponential algorithm **remains unimplemented**. See
`EXACT_ORDER_OPTIMIZATION_V17.md`.

---

# Latest: v1.6.0

Implemented indexed exact bucket elimination, exact sparse hash-join nonzero contraction, quick-first planning and full portfolio fallback. Seeded differential tests and benchmark records accompany the source. **None of these implement the manuscript's D.3/D.4.4 subexponential algorithm; worst-case exponential runtime remains.**

# Latest addition: v1.5.0 adaptive exact contraction

Implemented: factor-model alternatives (original CNF, COPY3), min-degree/min-fill/weighted-min-fill planning, decomposition checks, exact Boolean variable elimination, separator component dynamic programming, caching, bounded index slicing, API/CLI/browser integrations. These are **conventional exact exponential-worst-case** methods and do not certify the paper's D.4.4 packing recurrence. For full mathematical scope see `ADAPTIVE_CONTRACTION_V15.md`.

---

# Implementation and verification ledger — v1.3.0

| Capability | Status | Evidence / limitation |
|---|---|---|
| Strict canonical CNF, DIMACS | Implemented | Parser and malformed-input tests |
| DPLL SAT / exact all-declared #SAT | Implemented, reference | Bounded by runtime/nodes; not a competitive industrial solver |
| Witness validation | Implemented | CNF and entailment checked by independent evaluators |
| Deterministic propositional parser | Implemented | **Not** a natural-language parser; requires user semantic review |
| Definitional Tseitin encoding | Implemented | Unique extension preserves count if auxiliaries treated consistently |
| Independent small-instance counting | Implemented | Exhaustive enumeration (n<=12 in API) |
| Ganak adapter | Optional, UNVERIFIED | CLI binary must be separately installed; output contract varies by release |
| Independent UNSAT proof checking | Implemented (bounded DPLL-tree) | `solvers/certificates.py`; independent tree checker; not LRAT/DRAT, exponential-size worst case |
| Proof-carrying exact #SAT (bounded) | Implemented | `solvers/count_certificates.py` has independent complete Shannon-tree checker; no succinct proof guarantee |
| Clause-violation polynomial | Implemented, research | `research/violation_polynomial.py`; generic polynomial tensor elimination, exponential worst case |
| Safe 2-adic coefficient truncation | Implemented, research | Exact modulo 2^p; **not** the manuscript's mode pruning construction |
| Integer nonzero-node reconstruction | Implemented, research | Integral finite-difference interpolation recovers H(0), without asymptotic speedup |
| General SMT / Z3 adapter | Not implemented | Not silently synthesized |
| Existential projected counting | Implemented (bounded) | Witness blocking, 12 projected variables maximum; differential oracle |
| Weighted counting | Not implemented | Exact rational/weighted counts not included |
| Local hash-chained audit | Implemented | NOT an adversarially immutable ledger |
| Boolean clause / equality tensor conversion | Implemented | Dense tables; strict degree bounds |
| Generic tensor contraction | Implemented | Edge enumeration or standard bucket elimination |
| 2-adic and parity identities | Implemented as toy references | Exact modulo integers, tests, no theorem reproduction |
| Hermite / Boolean Möbius | Implemented as toy references | Bounded polynomial degree |
| Split-wire polynomial deformation | Implemented, limited research | `research/wire_deformation.py`: exact degree-E toy deformation with factorized nodes and exhaustive oracle, **not Cauchy construction** |
| Original ETH local Cauchy deformation | **Exact small-reference formulas (76)–(77)** | `research/cauchy_deformation.py` uses rational polynomial W and exhaustive `4**M` enumeration; not the entire low-width packet schedule or recurrence |
| Shifted Cauchy local coordinates | **Exact bounded reference** | Odd-denominator 2-adic integral jets, modulo `2**p` with full polynomial cross-check; not full weighted mode factoring |
| Node-matching local Cauchy cross modes | **Bounded reference implemented** | `research/cauchy_modes.py`: exact expanding, 2-adic/z-degree-certified pruning, 213 independent checks; **NOT paper D.4.4 low-rank grouped modes** |
| Guarded finite-ring Hermite reconstruction | **Bounded reference implemented** | `research/hermite_ring.py`: exact inverse functional, necessary input precision guard *sufficient*, 95 cross checks; **NOT full D.5 schedule** |
| Original collision packing / low-rank weighted modes | Not implemented | Paper-specific D.4.4 grouping/complexity reduction not reproduced |
| Exact grouped local Cauchy coefficient ranks | **v1.0 implemented** | Rational rank-one decomposition by Taylor order, reconstructed and checked against direct local jets. Not the paper's weighted modes |
| Generic recursive separator contraction | **v1.0 implemented** | Balanced exact factor cut with cut-edge assignment enumeration and time/call/cut limits; not the paper recursion |
| Original ETH recursive contraction theorem | Not implemented | No subexponential runtime claim for this code |
| Original Lean proof local rebuild | Not performed | Requires checkout + pinned toolchain; `audit_lean.sh` is helper only |
| External identity or evidence provenance | Not implemented | Inputs are locally submitted untrusted strings |
| Formal equivalence and counterexamples | Implemented | Original expressions independently evaluated on checked counterexample; optional checked proof |
| Production remote authentication and process isolation | Not implemented | Local use only |

## Evidence taxonomy

- `COUNT_PROOF_CHECKED`: a complete Shannon exact-counting certificate was independently verified against the original CNF; restricted to bounded instances.
- `WITNESS_CHECKED`: solver produced a complete model and a separate evaluator checked it.
- `PROOF_CHECKED`: complete bounded UNSAT tree verified by a separate checker from the original CNF. Not an industrial LRAT/DRAT proof.
- `SOLVER_ONLY`: solver asserts a result; no independent checked UNSAT certificate.
- `EXACT_ALGORITHM`: reference or external exact counting procedure reported a count, without a second cross-check.
- `CROSS_CHECKED`: an independent exhaustive enumerator agreed for small input n.
- `RESEARCH_ONLY`: experimental/reference mathematical computation, not production certification.
- `RESEARCH_CROSS_CHECKED`: tensor calculation agreed with exhaustive enumeration for small n.
- `NONE`: no completed mathematical result.

## CI and release blocking

Mismatches between the oracle and any reference algorithm block release. CI tests do not independently validate upstream mathematical proofs. The PDF analysis and source discussions must be distinguished from checked code.

## v1.1 additions (bounded and checked, not a full paper reproduction)

| Component | Status | Scope |
|---|---|---|
| Finite packet collision optimizer | Implemented | Exhaustive optimum <=8 wires when budget completes, otherwise deterministic local swap. Objective differs from the manuscript packet-collision theorem. |
| Modular Cauchy-jet polynomial factor elimination | Implemented | Exact finite-ring sum-product contraction on 2M half-edge variables; exponential in induced width, not subexponential recursive modes. |
| Independent cross-check | Implemented | Exhaustive `4**M` half-wire oracle for <=6 wires; same permuted network when packet optimization is requested. |
| Full manuscript weighted low-rank mode recursion | NOT IMPLEMENTED | No performance or completeness claims. |

## v1.2 additions — exact bounded research, no ETH speedup

| Component | Status | Scope |
|---|---|---|
| Coefficient-wise low-rank Cauchy modes with 2-adic weight | Implemented and checked | A whole mode is removed only if its minimum entry valuation is >= p. Coefficient matrix is independently reconstructed in Z/2^p. |
| Explicit recursively built child tensors | Implemented and checked | Each tensor exposes exactly the boundary half-wire assignments; child products are summed over internal interface variables. Exponential in boundary width. |
| Small-instance independent oracle | Implemented | Compared to exhaustive shifted Cauchy contraction, up to 6 edges. |
| ETH manuscript D.4.4 weighted packing and subexponential child-network theorem | **Not implemented** | No claimed asymptotic improvement. |

## v1.3 additions — end-to-end count recovery

| Component | Status | Verification boundary |
|---|---|---|
| Multiple independent Cauchy nodes and Hermite | Implemented, bounded | Exact weights and guard bits, computed from 2-adic valuations |
| Weighted mode child-tensor jets → exact integer #SAT | Implemented, bounded | Only when `p>=n+1`, at most six wires, exponential worst-case |
| Per-node exhaustive jet replay | Implemented | Independent exhaustive shifted rational evaluator |
| Original count comparison | Implemented | Conventional exhaustive contraction of original network |
| Replay transcript SHA-256 | Implemented | Binding/detection of alteration; hash is **not** a mathematical proof |
| D.4.4 asymptotic packing / D.5 schedule | **Not implemented** | No ETH speedup claimed |


## v1.4: bounded-degree exact tensor encoding

- **Implemented:** constant-degree equality-tree/COPY3 gadgets replacing
  dense high-degree source variable tensors without changing the number of
  satisfying assignments.
- **Implemented:** bounded deterministic min-neighbor exact integer and
  modular variable elimination, with explicit budgets and diagnostic trace.
- **Implemented:** API, CLI, browser UI, repeatable random differential
  validation and provenance records.
- **Not implemented:** paper's formal counting-preserving sparsification,
  its D.4.4 packet collision schedule, its weighted-mode complexity theorem,
  or subexponential recursive contraction.

## v2.4 exact marginal inference

- **Implemented and independently replay checked**: posterior marginals for all variables under explicit independent normalized rational priors, including zero-weight branches and free variables.
- **Still missing**: manuscript D.3 quantitative packing and D.4.4 subexponential recursive contraction.

Release tested on Python 3.13; Windows PowerShell entrypoint is included but Windows was not executed in this Linux environment.

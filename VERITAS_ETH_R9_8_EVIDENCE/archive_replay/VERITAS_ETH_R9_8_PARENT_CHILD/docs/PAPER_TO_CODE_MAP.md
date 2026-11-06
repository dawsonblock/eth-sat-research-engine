## v2.3 exact rational weighted model counting (outside paper proof)

`solvers/weighted_dag.py` implements exact rational WMC and replay-checked
component-DAG certificates; `solvers/conditional.py` computes independent
Bernoulli conditional probabilities. These are conventional exponential
worst-case algorithms, **not** manuscript D.3 packing, D.4.4 recursive
contraction, or evidence for the claimed subexponential bound.

---

## v2.2 reference-counting upgrade

`solvers/count_dag.py` adds an exact, bounded, replay-checked component-DAG
#SAT certificate with unit propagation, factor products, free-variable counts
and memoization. The checker recomputes the residual problems and counts;
formal verification of its reduction kernel is not claimed. This is a
conventional counting algorithm, **not** manuscript D.3/D.4.4 and not
subexponential-time.

---

# Scope ledger: manuscript vs runnable reference implementation

| Manuscript theme | Module | Actual coverage |
|---|---|---|
| Clause satisfaction indicator | research/algebra.py | Exact arithmetic with small truth-table tests |
| Even/odd modulo 2^ell polynomial | research/algebra.py | Pointwise identity validated for bounded levels/integer ranges |
| 2-adic divisibility/truncation | research/algebra.py | Generic integer v2 and modulo arithmetic only |
| Boolean differences / Taylor recovery | research/algebra.py | Boolean Möbius reference |
| Hermite interpolation | research/algebra.py | Exact rational confluent interpolation (degree <= 27) |
| Counting-preserving sparsification | Not implemented | Mathematical design task, no code |
| Cauchy polynomial wire deformation (D.4.3, 76–77) | **Local kernel and tiny full F(T) implemented** | `research/cauchy_deformation.py`: exact rational W polynomial; exhaustive F(T) for small CNF tensor networks; **not** collision packing or efficient recurrence |
| Exact split-wire interpolation (v0.7, outside paper) | research/wire_deformation.py | Polynomial K_T=1 or T; degree E, factorized ±1 nodes, full small oracle |
| Exceptional measurement-subspace projection | Not implemented | Required for first algorithm |
| CNF tensor conversion | research/tensor.py | Dense equality and clause tensors, exact |
| Ordinary tensor contraction | research/tensor.py | Full edge enumeration / standard bucket elimination |
| Exact violation generating polynomial | research/violation_polynomial.py | Generic polynomial tensor contraction; NOT the paper's Cauchy deformation |
| Cauchy shifted 2-adic local coordinates | **Bounded reference implemented** | `shifted_integral_kernel` and modular jets, odd denominators inverted exactly; lacks the **paper-specific grouped low-rank** mode construction |
| Exact coefficients modulo 2^p | research/violation_polynomial.py | Safe arithmetic and divisibility-based omission; NOT mode valuation construction |
| Exact nonzero-node interpolation | research/violation_polynomial.py | Finite differences, not Cauchy deformation |
| Bounded proof-carrying exact #SAT | solvers/count_certificates.py | Exhaustive Shannon counting tree with separate checker, not ETH speedup |
| Node-matched small local cross modes | **Bounded reference implemented** | `research/cauchy_modes.py`: exact valuation/z-degree-certified truncation, independently matched jets; not paper D.4.4 low-rank grouped modes |
| Finite-ring Hermite recovery (bounded variant) | **Bounded reference implemented** | `research/hermite_ring.py`: exact rational functional and sufficient modular guard; not the paper D.5 multiplicity/precision schedule |
| Manuscript packet collision packing / symbol-group modes | **Not implemented** | D.3–D.4.4 collision bounds, weighted group modes and recursive children not reproduced |
| Exact per-coefficient grouped Cauchy rank modes | **Bounded exact v1.0 reference** | `research/grouped_cauchy.py`: rational rank-one decomposition of each cross-group coefficient matrix; full 4**M jet oracle, no D.4.4 asymptotic mode bound |
| Balanced factor separator recursion | **Bounded exact v1.0 reference** | `research/recursive_separator.py`: ordinary cut-edge conditioning with recursively contracted factor groups; exponential worst case, not manuscript recursion |
| Original recursive ETH contraction | **Not implemented** | The v1.0 conventional separator recursion is separate and cannot inherit the paper’s bound |
| Bounded DPLL UNSAT refutation (outside paper) | solvers/certificates.py | Independently checked search-tree certificate; not ETH-specific |
| Projected #SAT enumeration (outside paper) | solvers/projected.py | Existential count through complete witness blocking, not subexponential |
| Lean comparator proof | scripts/audit_lean.sh | Manual build helper, theorem not reproduced |
| Finite factor-incidence packet optimizer (v1.1) | **Bounded exact/heuristic** | `research/packet_schedule.py`; NOT the paper D.3 collision-packing theorem. |
| Cauchy polynomial-factor elimination (v1.1) | **Bounded exact modular jet** | `research/cauchy_elimination.py`; generic treewidth-exponential elimination, NOT D.4.4 weighted low-rank child modes or ETH recursion. |

**Primary reference:** https://github.com/openai/math/blob/main/lean/docs/378.md

Do not state that the sharper manuscript exponent is formally proven by the weaker comparator statement. Keep exact theorem statements and local commit hashes when doing downstream Lean checks.


## v1.3 integration

- D.4.3 local polynomial: `cauchy_deformation.py`, unchanged exact small-kernel reference.
- Local coefficients and grouped modes: `weighted_children.py`, unchanged v1.2 small reference.
- Reconstruction from all nonzero nodes: `weighted_recovery.py`, **new end-to-end bounded integration** with guard bits and independently checked jets.
- Full asymptotic D.4.4 contraction and D.5 tapered interpolation: **not implemented**.


## v1.4 exact structural degree reduction

`research/bounded_degree.py` implements a **bijective extension** of CNF
assignments to a constant-degree tensor network. A degree-d equality tensor
is replaced by d-2 ternary equality gadgets (d >= 3), connected by d-3
auxiliary wires. Clauses are unchanged. Each complete original assignment
extends uniquely, so the partition function is identical to #SAT. For d = 0
an isolated source variable contributes the explicit scalar 2. A separate
`research/minfill_contract.py` provides a deterministic min-neighbor
exponential-time oracle with work, table and time caps. This realizes one
building block needed for bounded-degree networks but is **not** the
manuscript's D.4.4 collision-packing or subexponential recursion.

## v1.8 additional finite research utility

`src/veritas/research/optimal_packets.py` exact finite packet incidence-score partitioning: **engineering proxy only**, not a match to the paper-specific packing lemma. `src/veritas/research/cauchy_elimination.py` can opt into it; original proof and complexity bounds remain unimplemented.

## v2.1 finite packet branch and bound

`research/bounded_partition.py` and `bounded_partition_checker.py` optimize
a finite incidence-collision surrogate with a proved admissible lower bound
and optional independent small-instance subset-DP verification. **Not** the
manuscript D.3 packing theorem or D.4.4 recursive contraction.

## v2.4 posterior marginals (outside the ETH paper)

`solvers/marginals.py` adds all-variable exact posterior marginals using reverse-mode differentiation of the conventional weighted counting DAG. The replay checker validates the source DAG and derivatives using exact rational arithmetic. **Not** D.3 or D.4.4 and does not establish subexponential worst-case complexity.

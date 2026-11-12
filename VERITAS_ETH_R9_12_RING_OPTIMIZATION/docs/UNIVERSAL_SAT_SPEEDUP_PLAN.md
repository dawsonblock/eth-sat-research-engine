# Universal SAT speedup — research and engineering plan

**Status:** specification and roadmap only. VERITAS R9 does **not** yet provide a
universal subexponential 3-SAT solver. All `source_qualified` and
`subexponential_bound_evidence` flags remain **false** until explicit theorems and
pinned baselines are delivered.

This document adopts the guarantee framework requested for the program: a theorem
over **all** supported 3-CNF inputs **and** an implementation whose **total** work
is measured honestly.

---

## 1. Problem statement and outputs

### Input class

* **3-CNF** formulas in DIMACS or `veritas.core.cnf.CNF` form.
* **n** = declared variable count (including variables that appear in no clause).
* **L** = input length (bytes or literal count; fixed convention in benchmarks).

### Outputs (never conflate in benchmarks)

| Mode | Output | Extra cost |
|------|--------|------------|
| **Decision SAT** | SAT + one model, or UNSAT | Baseline for speed comparisons |
| **Exact #SAT** | Full satisfying assignment count | Must include counting overhead when compared to decision solvers |

A counting algorithm may decide SAT, but **T_decision** comparisons must not credit
#SAT paths that do extra work unless that work is counted.

### Target complexity guarantee (theorem lane)

For algorithm **A** on formula **F**:

\[
T_A(F) \le \mathrm{poly}(L)\, 2^{f(n)}
\]

with an **explicit** finite bound on the polynomial factor and on admissible **F**
(not “for some unspecified constant”).

**Subexponential** (research target, not proved):

\[
\lim_{n\to\infty} \frac{f(n)}{n} = 0.
\]

**Practical** (engineering target, separate from asymptotics):

* Pinned baselines (e.g. Kissat, CaDiCaL, or internal `adaptive_count` legacy path).
* Same task (decision vs decision, count vs count).
* Report **T_A** wall-clock + certified operation ledger, not asymptotic notation alone.

---

## 2. Total-work accounting (central mathematical test)

Any decomposition that replaces one instance by **q** children must satisfy:

\[
W_{\mathrm{new}}
=
W_{\mathrm{transform}}
+
\sum_{j=1}^{q} W_j
+
W_{\mathrm{reconstruct}}
+
W_{\mathrm{check}}.
\]

**Smaller children are not enough.** The sum must beat the parent cost.

Toy model (illustration only): parent cost \(2^s\), each child \(2^{\rho s}\), overhead ignored:

\[
\frac{W_{\mathrm{old}}}{W_{\mathrm{new}}} \approx \frac{2^{(1-\rho)s}}{q}.
\]

| q | Combined child work (ρ=0.9, s=80) | vs parent \(2^{80}\) |
|---|-----------------------------------|----------------------|
| 128 | \(2^{79}\) | ~2× saving |
| 256 | \(2^{80}\) | break-even |
| 1024 | \(2^{82}\) | ~4× **worse** |

**R9 implication:** circulant parent–child proofs at one jet point show **local**
factorization (\(C_{\mathrm{parent}} = \prod_g C_{\mathrm{child},g}\)) on a **bounded**
96-wire fixture. That is **not** a global \(W_{\mathrm{new}} < W_{\mathrm{old}}\) theorem
for arbitrary 3-SAT until:

1. A reduction embeds general 3-CNF into the contracted network with **proved**
   \(W_{\mathrm{transform}} + \sum W_j + W_{\mathrm{reconstruct}} + W_{\mathrm{check}} <
   W_{\mathrm{direct}}\).
2. **q** and **ρ** are uniform in **n** on the full input class.

Code hook: `veritas.research.sat_work_accounting.DecompositionWorkLedger`.

---

## 3. Current VERITAS map (honest baseline)

| Layer | What exists | What it is **not** |
|-------|-------------|-------------------|
| `CNF` | Validated 3-CNF, unused vars in **n** | Universal solver |
| `adaptive_count` | Exact #SAT via elimination / boundary DP | Subexponential; treewidth-dependent worst case |
| `parent_child_r912` elimination route | Width-bounded exact contraction | Exponential in verified width; interaction 96 needs width 17 |
| `parent_child_r913` fast jet solve | Fast \(C_{\mathrm{parent}}(\beta)\) on bounded interaction | Not wire elimination; not all 3-SAT |
| `research_spec` obligations | SAT decision obligation **unproved** | No theorem |
| Paper / R9.4 obligations | Outer #k-SAT reduction **open** | See `docs/R9_2_R9_4_PROOF_OBLIGATIONS.md` |

**Do not** promote PR #4 interaction reconstruction to a universal SAT speedup.

---

## 4. Research phases

### Phase A — Guarantee specification (4–6 weeks narrative; work is proof-shaped)

1. Fix **supported** 3-CNF class (max clause width 3, max L, or after preprocessing).
2. Write **T_A** as sum of named phases: parse, normalize, encode to network, contract,
   count, certify.
3. Separate **decision** and **#SAT** specifications and reduction costs between them.
4. List **failure/refusal** outcomes (resource limits) separately from complexity.

### Phase B — Work ledger calculus

1. For every proposed split (separator, packet group, mode bucket), register
   \((W_{\mathrm{transform}}, q, \{W_j\}, W_{\mathrm{reconstruct}}, W_{\mathrm{check}})\).
2. Prove inequalities on **rings** used (Boolean tables vs jet elimination vs resummation).
3. Identify **interaction** terms (mode coupling) that defeat naive \(\prod\) factorization.

### Phase C — Outer reduction (R9.4 open obligation)

1. Count-preserving arbitrary-density 3-CNF → source network (not fixed-density demos only).
2. Prove padding / parity / sparsification stages preserve satisfying assignments **and**
   admit a **uniform** decomposition with bounded **q** and **ρ**.
3. Only then attach inner contraction theorems.

### Phase D — Theorem \(T_A(F) \le \mathrm{poly}(L) 2^{f(n)}\)

1. Close recurrence for **f(n)** along the proved decomposition (not hand-waved).
2. Show \(\lim f(n)/n = 0\) **or** stop claiming subexponential.
3. Publish obligation closure in `research_spec` with `proved_in_this_repo=True` only when Lean/Python certificates exist.

### Phase E — Engineering parity with theorem

1. Implement **A** with the **same** phases as the proof.
2. Instrument each phase → `DecompositionWorkLedger` rows.
3. Regression: ledger sum matches wall-clock order of magnitude on micro-benchmarks.
4. Pinned baseline harness: decision SAT + #SAT suites, artifact JSON (see `scripts/bench_sat_methods.py` pattern).

---

## 5. Engineering workstreams (parallel to proof)

| ID | Deliverable | Acceptance |
|----|-------------|------------|
| E1 | `sat_universal_cli` — single entry, mode=`decision|count`, emits ledger JSON | **Scaffold:** `sat_universal.py` + `scripts/sat_universal_cli.py`; no silent fallbacks |
| E2 | Baseline matrix (pinned versions, seeds, timeouts) | **CI:** CaDiCaL `rel-2.1.2` + Kissat `rel-3.1.1` in `e2-external-baseline`; `cross_checks` on universal runs |
| E3 | Extend `DecompositionWorkLedger` through R9.10 recursive `contract` | **Done (scaffold):** each support-term child product logs ledger + stream event |
| E4 | Jet-point fast path **only** when certificate says `bounded_interaction` | Refuse otherwise |
| E5 | Document refusal vs speedup in user-facing API | Matches R912 preflight semantics |

---

## 6. Success criteria (both required)

**Mathematical:** Closed proof of \(T_A(F) \le \mathrm{poly}(L) 2^{f(n)}\) on the stated
3-CNF class, with optional \(\lim f(n)/n = 0\).

**Practical:** On pinned benchmarks, same-task comparison shows median improvement
with **no** false UNSAT / wrong count; overhead terms in §2 accounted for in the
ledger.

Improving a published asymptotic bound **without** E5-style measurement **does not**
satisfy the engineering requirement.

---

## 7. Immediate next steps (repo)

1. ~~Land `sat_work_accounting.py` and use it in R9.10 decomposition logging (E3).~~ **Done** — see `tests/test_r910_decomposition_ledger.py`.
2. ~~Add `tests/test_work_accounting_toy.py` encoding the ρ=0.9, q table in §2.~~ **Done**.
2b. ~~E1 reduction-first CLI scaffold~~ **Done** — `run_universal_sat` + `scripts/sat_universal_cli.py`; see `tests/test_sat_universal.py`.
3. Keep `fast_universal_parent_jet_solve` behind `finite_scaled_experiment` +
   layout certificates (E4).
4. Open Lean/Python checklist items from `docs/R9_2_R9_4_PROOF_OBLIGATIONS.md` for
   outer reduction (Phase C).

---

## References

* `docs/R9_2_R9_4_PROOF_OBLIGATIONS.md`
* `docs/R912_EXACT_ELIMINATION_ROUTE.md`
* `src/veritas/research/parent_child_r913/research_spec.py`
* `docs/R913_COEFFICIENT_EXTRACTION_RESEARCH.md`

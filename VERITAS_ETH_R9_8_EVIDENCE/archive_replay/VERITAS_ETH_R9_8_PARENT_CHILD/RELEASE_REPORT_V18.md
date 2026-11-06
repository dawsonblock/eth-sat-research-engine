# VERITAS-ETH v1.8.0 — Release report

## Implemented

- Exact, bounded **subset dynamic programming** for a finite packet-incidence collision objective. Searches packet partitions rather than factorially many wire permutations. Handles a final partial packet correctly. Deterministic lexicographic tie-breaking.
- Checks the selected score independently using `collision_score`; reports `RECOMPUTABLE_EXHAUSTIVE_SUBSET_RECURRENCE` evidence.
- Explicit `PacketPlanningLimit` for timeout, state and transition budgets. Never returns a purported optimum on truncated search.
- API, CLI and browser interfaces; optional use before exact modular Cauchy polynomial elimination. Legacy planner remains the default.
- Small exhaustive-permutation oracles, 15-wire comparisons, tested count-preserving relabeling, small independent Cauchy jet oracle and adversarial factor-network case.

## Performance findings

- A fixed 12-wire tensor network yields collision score **6** for the previous local-swap heuristic and **5** for exact subset DP, both with maximum incidence **2**.
- Additional small benchmarks show mixed planning overhead: DP is often faster than full permutation search for <=8 wires, but can be slower than the local-swap heuristic on larger networks. These are machine-specific measurements and do not guarantee any reduction in overall exact-count runtime.

## Mathematically unimplemented

The paper-specific D.3 packing schedule and its asymptotic collision bound, the quantitative D.4.4 weighted-mode-count analysis, the specialized subexponential recursive contraction theorem and the complete formal source proof reproduction remain **unimplemented**. This project still has exponential worst-case complexity.

See `docs/EXACT_PACKET_PARTITION_DP_V18.md` and `docs/IMPLEMENTATION_STATUS.md` for the precise scope.

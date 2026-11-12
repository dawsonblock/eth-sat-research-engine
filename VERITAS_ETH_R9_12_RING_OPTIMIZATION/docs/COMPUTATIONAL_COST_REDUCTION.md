# Computational cost reduction (engineering plan)

This note maps the Hexagon / R9 engineering recommendations to concrete
modules in this checkout. It does **not** implement Anthropic's full
subexponential construction or claim any new complexity theorem.

## Priority modules

| Priority | Module | Role |
| --- | --- | --- |
| 1 | `veritas.research.anthropic_eight_square` | Exhaustive finite checks of Eq. (12) over 4096 settings and Eq. (28) over all block quadruples; static row/column bit-cost proxy |
| 1b | `veritas.research.anthropic_signed_contraction` | One-level crossing rewrite bit-cost proxy with expansion overhead vs direct evaluation |
| 2 | `veritas.research.cost_ledger` | Tree-wide work, cache hit rate, unique subproblems, optional recursive budget |
| 2b | `veritas.research.cost_ledger_bridge` | `RecursiveVisitTracker` attached to R9.9 streaming and R9.10 numerical executors (`tree_ledger` field) |
| 3 | `veritas.research.hybrid_router` | Chooses conventional boundary DP vs elimination using planner estimates |
| 3b | `veritas.research.cnf_structure` | Count-preserving disjoint component product (`structure_aware_count`) |
| 3c | `veritas.research.cnf_preprocess` | Unit propagation, tautology/duplicate removal (#SAT-preserving) |
| 3d | `veritas.research.gf2_xor_count` | Pure GF(2) XOR systems via elimination (`2^{n-rank}`) |
| 3e | `veritas.research.gf2_xor_mixed` | Mixed CNF+XOR via null-space conditioning (`max_xor_enum_bits` cap) |
| 3f | `veritas.solvers.external_baselines` | Optional Ganak/CADICAL cross-check vs internal counts |
| 4 | `veritas.research.adaptive_contract` | Existing exact #SAT path (unchanged semantics) |
| 5 | `veritas.research.boundary_dp` | Separator / component memoization (existing) |

Anthropic and OpenAI manuscript recursion remain experimental backends only.

## Commands

```bash
cd VERITAS_ETH_R9_12_RING_OPTIMIZATION
export PYTHONPATH=src

# Eight-square identity gates
python scripts/validate_cost_reduction_gates.py
python scripts/experiment_r913_signed_contraction.py

# Wire scaling smoke (8/10/12 wires)
python benchmarks/v28_cost_scaling.py
python benchmarks/v29_structural_hybrid.py
python scripts/profile_cost_receipt.py examples/example.cnf --structure
python benchmarks/v30_xor_preprocess.py
python benchmarks/v31_external_baselines.py
```

Pure XOR (no CNF clauses), equations in JSON:

```bash
veritas-cli run --structure-hybrid-count --xor-equations xor.json /dev/null
# xor.json: [{"variables":[1,2],"rhs":1},{"variables":[2,3],"rhs":0}]

# Hybrid routing on a tiny CNF
python -c "from veritas.core.cnf import CNF; from veritas.research.hybrid_router import hybrid_count; print(hybrid_count(CNF.from_lists(4,[[1,2],[3,4]]), timeout_s=5)['routing'])"
```

## Correctness vs performance

Preprocessing transformations used for **#SAT** must be count-preserving or
supply an exact reconstruction rule. The hybrid router only affects which
**conventional** exact engine runs; it does not weaken certificate semantics.

## What remains open

- Full two-active-level R9 numerical execution under source qualification
- Ganak installed (`VERITAS_GANAK`) for full external model-count parity in `v31` benchmarks
- Integrated XOR elimination backend for mixed CNF/XOR instances
- Production bit-operation accounting across the entire R9 recursive tree

Run `pytest tests/test_anthropic_eight_square.py tests/test_cost_ledger.py tests/test_hybrid_router.py` before treating these gates as green.

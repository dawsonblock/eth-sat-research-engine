# v1.3.0 — End-to-end weighted Cauchy / Hermite exact-count reference

## Mathematical contract

For a CNF with `n` declared Boolean variables, build the bipartite tensor network with `M` wires. The D.4.3 packet kernel defines a polynomial `F(T)` with `F(0) = #CNF` and a degree bound `D = M(2L-1)`.

Use nonzero nodes `t ∈ {-L, …, -1, 1, …, L-1}` for `L=1 or 2`. At every node, calculate a truncated jet `F(t+2L z) mod (2^q,z^m)`, with `m = ceil((D+1)/number_of_nodes)`. Since `number_of_nodes * m ≥ D+1`, exact confluent Hermite weights `w_(t,j)` exist and satisfy `F(0) = Σ w_(t,j)[z^j]F(t+2Lz)` over rationals.

The previous v1.2 code reconstructs coefficient-wise Cauchy rank-one modes and contracts polynomial-valued boundary tensors at **one** node. The new orchestrator repeats this computation at all nonzero nodes, tracks exact valuations of interpolation weights, and selects `q = p + guard_bits` to recover `F(0) mod 2^p` without unsafe division. `p=n+1` suffices to recover the exact integer count because `0 ≤ #CNF ≤ 2^n`.

**Critical distinction:** this use of nonzero nodes is NOT the manuscript's tapered multiplicity scheme; the grouped modes are coefficient-wise rational rank factorizations, not its new asymptotic mode bound. Complexity remains exponential in general.

## Modules and interfaces

- `research/weighted_recovery.py`: `recover_weighted_count`, `verify_recovery_transcript` and `RecoveryBudgetExceeded`.
- `research/weighted_children.py`: exact mode reconstruction and recursive child tensors (inherited v1.2).
- `research/hermite_ring.py`: independently solves an exact Hermite linear functional and computes guard bits.
- `research/cauchy_deformation.py`: independent exhaustive half-wire jet evaluator.
- `api/main.py`: `POST /v1/research/weighted-recovery`.
- `cli.py`: `veritas-cli cnf file.cnf --weighted-recovery --packet-size 2 --timeout 15`.
- `scripts/validate_v13.py`: 300 seeded random independent-count comparisons.

### API request

```json
{"n": 3, "clauses": [[1, 2], [-2, 3]], "packet_size": 2, "group_span": 1, "timeout_s": 15, "cross_check": true}
```

An omitted `precision_bits` means exact count with `p=n+1`. A smaller explicit `precision_bits` returns `COUNT_RESIDUE`, with `exact_count=null`, even when the integer result happens to be representable with fewer bits. The output includes node jets, reconstruction weights, guard precision, and a transcript hash. Resource failure returns `UNKNOWN` with no count.

## Verification model

Three distinct checks are intentionally separated:

1. **Arithmetic verification:** check interpolation weights, sample multiplicities and modular reconstruction, plus a SHA-256 transcript binding inputs and claimed residues. The hash is an identity check, not a cryptographic mathematical proof.
2. **Independent jet verification (optional):** recompute every node by exhaustive shifted rational Cauchy half-wire enumeration, separate from the weighted recursive implementation.
3. **Independent original-count verification (optional):** contract the original undeformed network with conventional exact edge enumeration and compare to the recovered residue.

`verify_recovery_transcript(..., replay_jets=True)` recomputes the independent jets and original count. An independently replayed transcript is evidence for correctness **on the given bounded instance**, not a succinct proof or an asymptotic theorem.

## Resource and trust boundaries

- `packet_size`: 1 or 2; `edges ≤ 6`; `variables ≤ 24` enforced at API level; max 128 input precision bits to child evaluator; max 20 coefficients per local jet.
- Global execution deadline and total work-assignment limit apply across all node calculations, not separately reset for each node.
- `max_boundary_vars` and `max_table_entries` prevent unbounded child tensor tables; these checks are safeguards, not an OS-enforced memory sandbox.
- API is designed for loopback use and has no remote authentication. Do not deploy publicly.
- The upstream Lean proof is not built or replayed here; paper D.4.4 collision packing and the subexponential recursion remain **NOT IMPLEMENTED**.

## Tests

```bash
python -m pytest -q
python scripts/validate_v13.py
python scripts/validate_v12.py
python scripts/validate_10000.py
python scripts/verify_manifest.py
```

The correct release standard is zero mismatches on tested cases and explicit failure for exhausted budgets. Passing tests cannot establish the manuscript's asymptotic bound.

# VERITAS-ETH v2.6.0 — Release validation and mathematical scope

## Baseline and software changes

Extracted and extended v2.5 source. Retained pre-existing SAT, #SAT, tensor, certificate, arithmetic, CLI, API, interface and regression modules. New `eth_packing_v26` is separate from earlier packet heuristics, enabling direct comparison without silent replacement.

New operations:
- Exact coordinatewise conditional-expectation derandomization for **directed pair-label squared loads**, using separate row and column vertex symbols.
- Canonically padded uniform `H_pad` for every directed class; all unordered symbol pairs enumerated and orientation bits enforced.
- Independently replayed conditional-expectation certificates, per-wire coverage and padding checks; fail-closed on oversized inputs or invalid data.
- D.6 numeric predicates, parameter schedule correction from floor to ceiling, read-only research API/CLI/GUI endpoints.

## Validation in local Linux environment

- `pytest -o addopts='' -q`: **360 passed**, including **11 new v2.6 tests**.
- `scripts/validate_v26.py`: **150** seeded instances, **1,438** transcript assignments replayed, **143** malformed certificates rejected. Also a 128-edge finite numeric-D.6 example.
- `scripts/validate_10000.py`: **10,000** inherited SAT/count comparisons plus 106 tensor comparisons passed.
- `scripts/smoke.py`: PASS.
- `benchmarks/v26/d3_packing_bench.py`: five diagnostic cases of 8, 16, 32, 64, 128 edges, independently verified, with timings captured in build log. These are **not solver speedups**.

## Finite example and context

For the explicitly scaled `r=2`, `a=1` 4-regular bipartite example, `M=128`, `D=4`, `L=2`, `delta=4`, `H_pad=32`, and `packet_count=64`. The three D.6 **numeric** inequalities hold exactly: `128>=2*4^2*4`, `128>=2*4`, `2*2<=4`. This is not the paper's fixed radix `r=64` or its full active-call parameter schedule. It demonstrates a finite mathematical construction, **not** a full reproduction of the ETH result.

## Corrections to inherited v2.5

- The manuscript's displayed `u_d` expression uses **ceil**; v2.5 implemented **floor**. This error is corrected, with a corresponding regression test adjustment.
- The earlier `eligible` flag incorrectly treated `u_d>0` as sufficient. v2.6 treats it only as a numeric D.6 check when `M` and `delta` are explicitly supplied; it is not the full theorem's eligibility or a speed claim.

## Remaining proof/engineering gaps

No D.4.4 weighted-tile geometric cross-mode expansion, child construction satisfying the theorem's recursion invariant, upper bound on retained mode tuple counts, full finite-ring tapered Hermite recursion or polynomial-space demonstration. The software remains exact but exponential-worst-case for general #SAT.

## Reproduction

```bash
python -m pip install -e '.[test]'
python -m pytest -o addopts='' -q
python scripts/validate_v26.py
python scripts/validate_10000.py
python scripts/smoke.py
python scripts/verify_manifest.py
```

A file SHA-256 manifest is included in the final ZIP. It detects accidental modification, not a trusted code-signing identity.

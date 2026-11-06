# VERITAS-ETH v1.7.0 release report

## Baseline and scope

Full cumulative upgrade of the v1.6.0 source archive. New code is limited to
finite exact elimination-order optimization of the original CNF factor model,
plus corresponding API/CLI/browser integration and validation. All earlier
reasoning, #SAT, Cauchy and tensor research modules remain in this archive.

## New capabilities

1. Work-optimal subset DP for <=12 original-CNF variables under the declared
   dense-work objective and independent graph-fill order replay.
2. Minimum-induced-width exact DP with a second pass optimizing work within
   the global width bound.
3. `--adaptive-portfolio optimal_small` for counting with an optimal proxy
   order; no silent separator substitution.
4. `--optimal-order-report` CLI and `/v1/research/optimal-order` API for
   reporting an optimal finite plan **without computing a #SAT count**.
5. Fail-closed search cap and deadline, deterministic testing and benchmarks.

## Measured behavior

See `validation/benchmark_v17.json`. A fixed nine-variable counterexample
reduced the dense cost proxy **222 -> 190** and induced width **5 -> 4**.
Median end-to-end time nevertheless rose in the measured tiny instance because
exhaustive subset planning takes more CPU time. Other benchmark cases
showed equal proxy costs and slower total execution. Therefore this version
**does not establish a general end-to-end performance advantage**.

## Mathematical nonclaims

A finite-state optimal elimination ordering is not the paper's D.3 packing
lemma, not a D.4.4 mode construction, not a proof of subexponential
complexity, and not formal Lean verification. Existing reference algorithms
remain exponential in worst-case induced width and/or the number of variables.

## How to reproduce

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v17.py
python benchmarks/v17_optimal_order.py
python scripts/validate_10000.py
python scripts/smoke.py
python scripts/build_release.py
python scripts/verify_manifest.py
```

`validation/validation_v17.json` contains deterministic independent
comparison counts, including brute-force permutation order checks.

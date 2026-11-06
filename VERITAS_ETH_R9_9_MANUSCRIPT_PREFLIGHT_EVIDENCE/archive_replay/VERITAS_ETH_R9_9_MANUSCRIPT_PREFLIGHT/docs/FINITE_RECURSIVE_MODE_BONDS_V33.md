# v3.3 exact recursive mode-bond contraction

The implementation recursively conditions on a geometric-mode exponent and computes an exact sum-product over the residual factors. It recognizes disconnected components and memoizes identical residual subproblems. The algebraic domain is the same truncated extension-ring jet implementation used in v3.2.

For factors $T_g(\beta|_{I_g})$, the finite invariant is

$$Z=\sum_{\beta}\prod_g T_g(\beta|_{I_g}).$$

Conditioning on one exponent $b$ gives $Z=\sum_b Z_b$; disconnected components multiply. Zero entries can be removed. No floating point arithmetic is used.

## Validation

Each returned result must match (1) the earlier exact sparse bond-elimination implementation, and (2) independent direct Cauchy half-edge enumeration; the certificate checker regenerates all child entries and recursively replays the result. This is a reference method for at most 6 Cauchy wires, not a general #SAT acceleration.

## Explicitly not demonstrated

The recursion operates on **mode-index factors**. It does **not** build the manuscript's special group-local packet tensors, guarantee child wire count $M_{child}\le M/8$, or bound the total modes or bit complexity subexponentially. Factorization, conditioning and memoization may still take exponential worst-case time and space. Manually scaled parameters are not the manuscript's asymptotic theorem.

## Reproduction

```bash
python -m pip install -e '.[test]'
veritas-eth33 construct --n 2 --clauses-json '[[1,2]]' --output cert.json
veritas-eth33 check --certificate cert.json
python scripts/validate_v33.py
python -m pytest -q tests/test_v33_recursive_bonds.py
```

## Next proof and implementation obligations

Implement the paper-specific packet-tensor coefficient extractor and source-group linear forms, verify child degrees and wire counts, implement the full tapered precision schedule in every recursive descendant, then audit end-to-end mode count, polynomial space, and the subexponential recurrence.

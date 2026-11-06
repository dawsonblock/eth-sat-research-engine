# VERITAS-ETH v3.1.0

Preserves the cumulative v3.0.0 source, solvers, exact arithmetic, Cauchy kernels, D.3 packets, API/CLI/UI and tests. Adds:

1. Exact geometric-tile `j^b` modes over the truncated 2-adic extension ring, with formal Taylor coefficient calculations and valuation certificates.
2. Separate mode certificate checks, including direct Cauchy jet reconstruction, mandatory D.3 verification, precise metadata and canonical reconstruction.
3. Finite group-local, mode-indexed scalar child calculation, without cross-group boundary conditioning; cross-checked against independent full half-edge enumeration.
4. New `veritas-eth31` CLI, research API, browser demo, regression tests and release report.

**Not included:** the paper's recursion-specific child tensor size bounds, complete recursive contraction and asymptotic subexponential proof. Experimental modes never replace production SAT/#SAT calculations.

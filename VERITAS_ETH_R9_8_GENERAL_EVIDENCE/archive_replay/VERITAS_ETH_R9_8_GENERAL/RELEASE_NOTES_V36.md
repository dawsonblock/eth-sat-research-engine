# VERITAS-ETH v3.6.0

Adds exact finite packet-level polynomial coefficient tensors over truncated 2-adic extension jets. Each D.3 packet obtains its own exact Boolean multilinear coefficient table indexed by row-halfbit assignments and column monomial subsets. Coefficients are built with idempotent sparse polynomial multiplication and independently checked by Boolean Möbius inversion. The complete packet-factor network is contracted and compared with the independent direct Cauchy half-edge oracle.

Adds `veritas-eth36`, API endpoints `/v1/research/eth/finite-packet-tensors` and `/check`, browser demo, correctness/corruption/property tests, and validation scripts. All previous source retained.

**Unimplemented:** manuscript's specialized D.4.4 shrinking packet tensor *children*, preservation of mode-weight bounds through recursion, M/8 full-child bound and subexponential complexity guarantee.

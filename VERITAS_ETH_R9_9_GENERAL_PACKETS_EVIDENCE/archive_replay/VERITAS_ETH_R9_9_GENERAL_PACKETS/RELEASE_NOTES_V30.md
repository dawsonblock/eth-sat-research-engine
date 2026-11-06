# VERITAS-ETH v3.0.0 — bounded implicit child-tensor reference

Adds `eth_recursion_v30`, a D.3-group-aware implicit extension-ring Taylor-jet tensor executor with exact boundary summation and memoization. An independent half-edge enumerator checks each result; an independent `T=0` contraction verifies original exact-count preservation. Certificate replay rejects tampering. Includes `veritas-eth30` CLI, API, local UI, adversarial tests, mathematical documentation and strict time/work bounds.

**Important:** This is *not* the D.4.4 specialized weighted-mode child construction, not a `M/8` size-reduction proof, and not a subexponential algorithm. The manuscript-scale preconditions are reported separately and are generally false in these finite demos. v2.9 functionality is preserved.

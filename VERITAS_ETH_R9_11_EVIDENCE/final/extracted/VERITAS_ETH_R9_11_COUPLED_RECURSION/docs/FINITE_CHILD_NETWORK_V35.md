# v3.5 finite explicit child network / wire-scope audit

This release materializes an exact **finite** mode-bond child network from a previously verified D.3 packing and v3.3 recursive child tensor result. For each symbol group it records:

1. Original half-edge bits owned by its original vertex factors.
2. Geometric-mode exponent bonds incident on it, with two certified endpoints per bond.
3. Original local factor scopes and exact sparse group-tensor entry counts.
4. The complete finite child **index scope**: union of owned halfbit indices and mode-bond indices.
5. A bounded guard `max_child_scope` to prohibit too-large groups from being treated as completed computations.

The verifier recomputes the D.3 topology, checks the mode certificate and independent contraction oracles, recomputes each group from source material, and rejects an altered claim, wire count, endpoint, or exact result.

**Crucial distinction:** The finite child scope defined here is **not** the number of wires of the manuscript's D.4.4 recursively generated child tensor network. It is not sufficient to prove that claimed child network has at most `6M/r` wires. Both its number and total evaluation-cost bound still require dedicated implementation and proof. A numeric observation `8*scope<M` is reported only as a finite fact about this different scope, NEVER as a theorem.

Algorithmic cost remains exponential in general because the group table constructor sums assignments of local Boolean halfbits, and the exact mode-bond contraction can be exponential in active mode indices. v3.5 makes scope growth observable and rejectable; it does not lower worst-case complexity.

CLI: `veritas-eth35 construct --n 2 --clauses-json "[[1,2]]" --output child.json` then `veritas-eth35 check --certificate child.json`.
API: `/v1/research/eth/finite-child-network`, `/v1/research/eth/finite-child-network/check`, `/v1/research/eth/v35/status`.

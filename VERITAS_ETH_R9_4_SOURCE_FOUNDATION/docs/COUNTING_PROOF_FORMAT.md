# v0.6.0 — Bounded proof-carrying exact #SAT

A `veritas-shannon-count-tree-v1` proof is a JSON envelope containing the SHA-256 digest of the **exact** original CNF, a decimal integer `count`, and a tree rooted at `root`. A certified answer applies to **all declared Boolean variables**, including variables absent from the clauses. A proof generated for one CNF cannot be replayed against a modified formula.

## Node grammar

- `{"conflict": clause_index, "count":"0"}`: the identified original clause must be falsified by the path's current partial assignment.
- `{"satisfied": true, "count":"N"}`: every original clause must already be satisfied. `N` must equal `2^(declared_variables - assigned_variables)`.
- `{"unit": literal, "clause": clause_index, "next": node, "count":"N"}`: the original cited clause, simplified only by path assignments, must contain exactly that one distinct unassigned literal, and no assigned satisfied literals. The path follows that forced assignment. The count equals its child's.
- `{"split": variable, "false": node, "true": node, "count":"N"}`: the variable is unassigned, both Boolean branches are mandatory, and `N` is the sum of their counts.

The checker walks the tree independently of the generator, validates every local premise against the original formula, recomputes every node count, and checks the envelope claim. Missing branches, bad unit premises, unsatisfied `satisfied` leaves, wrong CNF digests, injected counts, invalid field names and resource overages fail closed. The proof is neither LRAT nor DRAT; its worst-case size is exponential. `COUNT_PROOF_CHECKED` means the full tree and count were independently verified, **not** that it was produced by a scalable counting algorithm.

## Security/resource limits

Proof generation: <= 26 variables, <= 80,000 nodes, <= 4 MB serialized, <= 30 seconds; default smaller. Checker: <= 80,000 nodes, <= 4 MB. Limits reject or return UNKNOWN, never assert the omitted parts of a search tree are complete. Proof verification is not a cryptographic attestation of the execution environment.

## Simple example

For `n=2, clauses=[[1]]`, variable 1 is forced true and the second declared variable is free; the correct count is 2. The proof is a `unit` node pointing to a `satisfied` leaf with count 2. For `n=1, clauses=[[1],[-1]]`, the root unit branch reaches an identified falsified clause and the certified count is 0.

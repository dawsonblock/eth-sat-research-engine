# VERITAS-ETH v3.7.0 — Reference D.4.4 group-local packet tensors

Introduces finite reference implementation of the manuscript's specific coefficient-extracted, fixed-mode-tuple group-local packet tensor construction. Mode exponent indices become frozen metadata and are not additional child-network wires. Counts original half-ports as child graph edges, performs exact target-mode coefficient extraction and source-mode substitution, and verifies the parent/child identity against independent direct Cauchy enumeration on bounded cases. Adds adversarial certificate checks and `veritas-eth37` CLI.

**Limitations:** Still relies on exhaustive group-local finite contractions. Does not implement complete recursively shrinking D.4.4 contraction at manuscript-scale parameters; does not prove M/8 under scaled test parameters, polynomial space, or subexponential time. API/UI additions from v3.6 remain unchanged.

See `docs/D44_GROUP_LOCAL_CHILD_SOLUTION_V37.md`.

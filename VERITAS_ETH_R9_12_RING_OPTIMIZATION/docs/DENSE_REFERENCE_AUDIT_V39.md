# Bounded dense-network reference audit

`scripts/validate_v39_dense_audit.py --wires M` runs one deterministic
two-table dense Boolean experiment for `M` in `8,10,12,14,16`. Set
`PYTHONPATH=src` or install the package first. The script records a hash for
each input table, finite mode counts, partial scalar-operation counts, the
largest retained tensor scope, a process peak-RSS observation, and resource
caps. Run each width in a fresh process when comparing peak RSS. These
statistics are not a complete work or storage ledger.

At `T=4` and modulo four, the two-slot Cauchy matrix is `3 I`. The separately
implemented `diagonal_node_four_oracle` uses the one-bit half-edge matrix
`[[1,2],[0,3]]` and an in-place Kronecker butterfly. It computes an
independent deformed residue and an integer reference dot product using a
`2^M`-entry table. Small cases also compare against direct half-edge
enumeration. It is an exponential-space reference, not a recursive solver.

The experiment's scalar mode sum must equal that independent deformed
residue. For zero reconstruction, it also attempts a separate finite
Hermite calculation at `M+1` target bits, enough to recover the complete
integer dot product of the Boolean tables, subject to operation and
live-jet-entry caps. A
`BLOCKED_RESOURCE_LIMIT` reconstruction is not a recovered count: the
reported original integer is the independent reference dot product.

For a node of Hermite multiplicity `q`, the reference computes only its
first `q` jet coefficients. Truncating each polynomial product modulo
`z^q` preserves these coefficients exactly. Its bounded half-edge check uses
`z=0` and `z=2^ceil(P/q)`, where `P` is the data precision: the omitted
integral tail then vanishes modulo `2^P`. This reduces finite work and table
size, but does not implement the manuscript's recursive theorem.

The mode experiment retains the original full-scope tensors, so its largest
child has `M` wires. It does not implement the v39 recursive children or
establish a reduction in total work. The table cap and scalar-operation cap
are preflight limits, not a hard operating-system memory or time limit;
peak RSS includes interpreter and process overhead. The v39 tapered
recursion itself remains capped at six nonzero parent wires.

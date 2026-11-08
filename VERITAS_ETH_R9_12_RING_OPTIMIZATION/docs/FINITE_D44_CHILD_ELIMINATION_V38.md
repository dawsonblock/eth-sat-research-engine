# v3.8 finite fixed-beta D.4.4 child tensor elimination

**Mathematical scope:** This upgrades the v3.7 finite group-local child reference, not the manuscript's full recurrence.

Given a fixed weighted mode exponent vector `beta`, each group-local child has original
vertices and newly constructed packet tensors. The global mode values are frozen
metadata, not wires. Every child edge is an original row/column half-port owned by
its symbol group. The v3.7 `_packet_value` function computes the exact coefficient
of the prescribed target powers in the group-local row polynomial and substitutes
source-group linear forms. This is the definition used by the v3.8 execution engine.

## Implementation

For group `g`, form factors `f_i` over their owned local half-ports. Original
vertex factors are integer-valued, lifted into the precise extension jet ring.
Packet factors are exact Taylor-coefficient tensors, built lazily and cached
across global mode tuples when their relevant local exponents are identical.

To eliminate wire `x`, replace the factors containing it by

```
  h(y) = f_1(y) ... f_k(y) summed over x in {0,1}
```

All operations are in `A_p[V]/(V^length)`. The algorithm chooses the variable
with fewest current neighbors, and refuses factor creation above the configured
`max_entries` budget. Disconnected components are contracted separately, and
packet-factor cache memory is capped in entries.

Summing products over the retained mode tuples yields the original deformed
network contraction *modulo* the configured ring precision. The resulting
jet is checked against the independent direct Cauchy half-edge oracle.
An optional second check runs the older exhaustive v3.7 reference. Independent
validation of finite instances is not proof of asymptotic complexity.

## API/CLI

```
veritas-eth38 construct --n 2 --clauses-json '[[1,2]]' --output result.json --cross-check-v37
veritas-eth38 check --certificate result.json
```

API: POST `/v1/research/eth/finite-child-elimination` and
`/v1/research/eth/finite-child-elimination/check`.

## Validation and restrictions

- The strict `M/8` numerical child flag is reported on each finite group, never promoted to a theorem.
- The source-replayed verification rejects changed input, computed result, metrics, resource policy or mathematical claim.
- Exact integer/ring arithmetic: no floating-point approximations.
- Finite network input is restricted by the inherited v3.1 geometric mode generator (at most six original wires).
- Worst-case complexity remains exponential in child width and retained mode count.
- Manuscript depth-dependent precision propagation is **not** implemented.
- The input source is not claimed to be an immutable pinned theorem revision.

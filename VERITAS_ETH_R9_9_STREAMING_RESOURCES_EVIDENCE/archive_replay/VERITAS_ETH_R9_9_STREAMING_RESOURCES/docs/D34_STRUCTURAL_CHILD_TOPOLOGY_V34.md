# v3.4: D.3 packing to finite D.4.4 mode-child structural bridge

## What is implemented

This release **recomputes and certifies** the incidence graph connecting real
half-edge ports, D.3 symbol groups, padded packet slots and the endpoints of
v3.1 finite geometric modes. It also composes that certificate with the
v3.3 exact recursive mode-bond contraction and checks that each computed
finite group tensor owns precisely the original half-ports and mode bonds
specified by the D.3/mode source certificates.

The independent checker rebuilds the complete ledger and replays both source
certificates; corruption in the port ledger, mode endpoints, a packet slot or
the computed algebraic result fails closed.

For each coordinate `d` of the verified packet labels, define:

- `R_g = {e: row_label[e][d] = g}`
- `C_g = {e: col_label[e][d] = g}`
- `H_g = |R_g| + |C_g|` original *real half-edge ports* in group `g`.

The program checks `sum_g H_g = 2M`. For D.3's finite symbol-port inequality,
`max_g |R_g| * r <= 3M` and `max_g |C_g| * r <= 3M`, so whenever this
finite inequality holds, `H_g <= 6M/r` follows by ordinary addition.

At `r=64`, this implies `H_g <= 3M/32 < M/8` for `M>0` **for the original
real half-ports only**. The production gate also checks all relevant D.6
numeric assumptions and the fixed manuscript radix. Test examples generally
use `r=2`, so they are explicitly *not* manuscript-eligible.

## What is NOT implemented or proved

**The actual recursively shrinking D.4.4 child tensor networks are missing.**
Those children include packet tensor factors and mode-extraction structure,
not just the original real half-ports. Consequently the real-port bound alone
cannot certify the manuscript's **total child wire count**. The v3.4 output
*always* sets `actual_recursive_child_wires_verified = false` and
`m_over_8_child_wire_theorem_proven = false`, even when a finite preflight
meets its numeric prerequisites.

The recurrence, total running time, polynomial-space bound, and complete ETH
reduction are not implemented or proved. The existing v3.3 recursion has
exponential worst-case complexity.

## Usage

```bash
pip install -e '.[test]'
veritas-eth34 construct --n 2 --clauses-json '[[1,2]]' --with-modes --output topology.json
veritas-eth34 check --certificate topology.json
veritas-eth34 contract --n 2 --clauses-json '[[1,2]]' --output combined.json
veritas-eth34 check --certificate combined.json
pytest -q tests/test_v34_child_topology.py tests/test_v34_bridge.py
python scripts/validate_v34.py
```

Local API operations: `/v1/research/eth/child-topology`, its `/check`
operation, `/v1/research/eth/checked-structure-and-contraction`, and its
`/check` operation. The research UI exposes the finite structural ledger.

## Next mathematical dependency

Build manuscript-specific packet tensor descriptions for each mode tuple,
then independently verify the **entire** child network has at most `6M/r`
wires and the stated maximum-degree bound. Only after that can the recursive
cost analysis be addressed. Do not substitute finite port-count measurements
for this missing construction.

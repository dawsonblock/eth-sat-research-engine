# R9.9 manuscript implementation: admission and remaining work

This checkout preserves the preceding supported-recursion release. It adds
explicit execution choices, a manuscript-bound obligation ledger, independent
port projection and resource preflight. It does not complete the source
executor, universal refinement or complexity proof.

`parent_child_r99.execution.ExecutionSpec` separates the finite schedule,
complete weighted enumeration or certified support, full tapered Hermite or
degree-certified Taylor recovery, and the leaf rule. Invalid combinations
are rejected. The source selector remains refused and cannot route to a
finite executor. Existing entry points retain their defaults.

`parent_child_r99.conformance.conformance_ledger()` checks all four pinned
manuscript hashes and binds obligations to the exact statement hashes. Each
obligation records its implementation, checker, present scope and remaining
work. Selecting a configuration does not prove its premises.

## Why the combined acceptance fixture currently cannot run

The full-grid executor recomputes every group for every retained tuple and
point. A nonleaf must pack whole vertices with side capacity
`floor(3M/64)`. Its smallest possible nonempty active descendant therefore
has at least 22 edges. Shrink requires its parent to have at least
`ceil(64*22/6) = 235` edges.

For every active coordinate there are at least two signed Hermite nodes.
Their full grids have at least `3M+1` points. With just one tuple per point,
one active descendant and 63 other group calls, a two-level successful
calculation needs at least

```
1 + 2*(3*235+1) * (63 + 1 + 64*2*(3*22+1))
= 12,199,681 calls.
```

The current `Policy` hard cap is 2,000,000 calls. This is a necessary cost
bound for the present recomputing executor, not a lower bound on tensor
contraction algorithms. Degree shortcuts, a different leaf rule or certified
reuse would change the premises. None is silently substituted into the
full-tapered acceptance criterion.

The new preflight checks actual occupied packet slots, inherited port order,
separate X/Y wires, child degrees, shrink, descendant capacity, full grids,
field size, precision and necessary call counts before rational Hermite
weights or mode tables are built. An optional prospective singleton layout
checks every descendant topology down to four-edge leaves. Unknown future
layouts remain marked incomplete. An executable point must still pass its
independent recipe and coefficient checks.

## Changing the number of groups

For the supplied 484-edge degree-two cycle, deterministic whole-vertex
singleton packing produces these actual structural results:

| Groups | Largest edges by depth | Full-grid call lower bound | Structural outcome |
|---|---|---:|---|
| 64 | 484, 44, 4 | 1,088,564,353 | Reaches leaves, exceeds current call cap |
| 128 | 484, 20 | Not completed | Descendant cannot pack a nonempty vertex |
| 256 | 484, 8 | Not completed | Descendant cannot pack a nonempty vertex |
| 512 | 484, 4 | 1,487,873 | Reaches leaves in one transition |
| 1,024 | 484 | Not completed | Root capacity one cannot hold degree-two vertices |

These lower bounds assume just one tuple per point. The comparison also
reports the exact original weighted count for the root singleton basis:
one at zero and `binomial(p_t+k-1,k)` at each nonzero residue point, where
`k` is the number of crossing packets. For 512 groups, `k=242`; this count
already exceeds the tuple budget. No tuple is dropped to make the report fit.
The displayed call bounds do not cover the cost of these extra tuples,
interpolation, entries or evidence. The supplied
cycle uses extension degree two; its full grid needs 1,453 distinct residues,
requiring degree at least 11. Its existing degree-zero experiment remains a
different calculation. General R99 packet execution still requires 64 groups;
the existing R98 configurable singleton driver is separate.

For `certified_support`, the full-tapered executor now uses independently
checked constant-row cancellation to simplify the point sum. Summing a
constant row's Y bit gives `(1-A)+A=1`; positive target-mode contributions
from that row vanish after summation. The original weighted inventory is
retained in the certificate, and no binary exponent restriction is imposed
on the other rows. The complete degree-bound grid and tapered functional
remain unchanged. This optimization does not establish generic feasibility.

## External commands

Run from this checkout, with a new output path outside it:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r99.preflight_cli \
  examples/r98_shrinking_cycle484.json \
  --compare-groups 64,128,256,512,1024 --max-calls 2000000 \
  --output ../VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_EVIDENCE/groups.json

PYTHONPATH=src python3 -m veritas.research.parent_child_r99.preflight_cli \
  examples/r99_nonconstant_matching242.json \
  --layout-file examples/r99_nonconstant_matching242_layout.json \
  --schedule 1:1,1:1 --max-points 4096 --max-calls 2000000 \
  --descendants singleton_first_fit \
  --output ../VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_EVIDENCE/matching.json
```

The second command is expected to refuse full-grid execution with a
machine-readable gap report. `--count-point NODE RESIDUE_INDEX` additionally
builds and independently verifies the complete mode count at one bounded
point without contracting any child. It is explicitly not complete-grid
tuple evidence. Resource refusals provide no result.

## Next implementation stages

1. Implement a replayable lazy mode inventory and independently certified
   aggregation that avoids materializing eliminated modes. Preserve the
   complete mathematical stream and arbitrary nonnegative exponents.
2. Add streamed full-tapered recursive evidence and an independent recursive
   consumer; the current full-tapered engine retains recovery records.
3. Measure arithmetic, entry, interpolation and evidence costs before
   increasing offline budgets. Preflight reports necessary bounds and raw
   coordinate storage, not a wall-clock or Python heap upper bound. A
   one-hour/four-GiB run must have external supervision; no such large run
   is automatically launched by this planner.
4. Seek the connected, multislot, nonconstant, exponent-two fixture with two
   active shrinking levels and complete tapered recovery. The separate
   passing component fixtures do not satisfy this combined criterion.
5. Generalize creation-precision tensor recipes and independent arithmetic
   through jet lengths greater than one; establish recursive closure.
6. Construct source-compliant padded packing under the exact schedule and
   prove its correspondence, child identity, precision recovery, termination,
   bit-operation and peak-space bounds. Keep source qualification disabled
   until those obligations have evidence.

Changing only the group count or a budget does not discharge stages 1–6.

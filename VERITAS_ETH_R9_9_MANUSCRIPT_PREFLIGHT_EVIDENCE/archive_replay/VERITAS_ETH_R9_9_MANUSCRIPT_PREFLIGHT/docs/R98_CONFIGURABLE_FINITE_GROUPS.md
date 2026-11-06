# Configurable groups in the finite shrinking experiment

Both finite drivers accept a fixed `groups` argument, with integer values
from 64 through 1,024 and default 64:

```python
contract_shrinking(parent, groups=512, policy=policy)
contract_general_shrinking(parent, groups=65, policy=policy, max_points=256)
```

The count is fixed throughout that invocation. The implementation does not
automatically select a count, switch counts at a descendant, or change the
manuscript's source schedule. `contract_source` has no group-count option.
Non-64 layouts are accepted only for `FINITE_SCALED_EXPERIMENT` with the
finite whole-vertex packing strategy. Legacy depth-limited point execution
and its certificate format retain their fixed 64-group boundary.

## Packing, immutable children, and source separation

For a parent with M edges and r groups, whole vertices are assigned separately
on each side using capacity `floor(3M/r)`. The packet layout stores `r`, the
class count `D=r^2`, exact edge coverage, orientation and actual side loads.
Vertices are not split; ordered inherited tensor ports remain unchanged.

Each retained exponent tuple produces exactly r children, including all
empty units. Every inherited Y and X half-edge is a distinct child wire.
The constructor and independent verifier both check

```
M_g = R_g + C_g,
r*R_g <= 3*M,  r*C_g <= 3*M,
r*M_g <= 6*M,  M_g < M.
```

Since r is at least 64, this also implies the original numerical `M_g < M/8`
bound for every positive parent. It does not establish source eligibility.
The source schedule still says r=64; the finite schedule separately records
the configured r. Child digests bind that schedule, and group indices are
validated against it. Changed counts, incomplete inventories, mixed schedules,
stale mode bindings and altered packet-class counts are rejected.

## Descendant and resource preflight

`group_preflight.py` independently projects the ordered topology to four-edge
leaves before any production contraction call. It uses no tensor values and
imports neither the production child constructor nor an entry evaluator.
It checks descendant packing, actual projected wire counts, degree, depth,
precision, complete tuple counts, calls and serialized evidence budgets.

The preflight stores a digest for every expected child topology. Every actual
generated child must match it before recursion. Prospective topology sharing
does not cache contraction values: every actual child is still recomputed at
every retained tuple and point, including empty units.

The constant-deformation driver has two points and one tuple at each active
node. Its complete conditional call count is

```
C(node) = 1 + 2 * sum(C(child)),   C(leaf) = 1.
```

For the general singleton grid, let k be the number of crossing packets,
`p_t=p+64M`, and `T=binomial(p_t+k-1,k)`. At zeta=0 the retained mode basis is
empty. At every nonzero residue interpolation point, zeta is a unit and the
diagonal Cauchy coefficient has valuation exactly two. Each crossing packet
therefore supplies one nonzero weight-one mode; higher geometric source forms
vanish because their tile quotient is zero. There are `3M` nonzero points per
Hermite node, giving

```
C(node) = 1 + 2*(1 + 3M*T) * sum(C(child)).
```

These counts are exact conditional on all arithmetic and tensor-family
admissions succeeding. Structural preflight supplies no contraction result
and does not certify those admissions. Runtime modes, tuples, independent
coefficient/point checks and exact recovery remain mandatory. Refusal at any
stage returns no result. The four-edge leaf threshold is unchanged.

The precision increment remains `64M` because `a=u=1`, not because of the
number of groups. It must not be replaced by `r*M`. Precision is checked at
every projected depth and again during execution. Work/time checks remain
cooperative; bit-time and peak-space bounds remain unestablished.

## Validated behavior

For the existing constant-row 484-edge cycle:

| Fixed groups | Outcome |
|---:|---|
| 64 | Existing 484 -> 44 -> 4 recursion; 5,761 actual calls |
| 128 | Refuses: 20-edge descendants cannot be packed with 128 groups |
| 256 | Refuses: 8-edge descendants cannot be packed with 256 groups |
| 512 | 484 -> 4; 1,025 actual calls; two complete points; exact 2^484 |
| 1,024 | Refuses: per-side capacity one cannot hold degree-two vertices |

The 512-group case uses 31,488-bit point precision. It passes with the total
call cap set to exactly 1,025 and refuses a cap of 1,024 before production
calls. This is a reduction in actual call count; it is not a runtime or
asymptotic speedup claim.

An admitted upper-limit case uses 1,024 groups on a 1,000-edge constant-row
cycle: 1,000 -> 4 edges, 2,049 actual calls, 65,024-bit point precision,
and exact result `2^1000` at target precision 1,024. The validation script
writes this generated input outside the source tree along with its evidence.

A nonconstant 22-edge matching also executes with 65 groups: 134 full-grid
points, 8,711 actual calls, and exact result `31^22`. No constant-row recovery
shortcut is used by the general driver.

The general 484-edge cycle at 512 groups has 242 crossing modes at a nonzero
point. Its complete tuple count is `binomial(31729,242)`, approximately
`3.78e615`. Preflight refuses this computation before any production calls;
it does not omit tuples or substitute an oracle answer.

## Commands and evidence

From this development checkout, keep outputs outside the source tree:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r98.shrinking_cli \
  examples/r98_shrinking_cycle484.json --groups 512 \
  --output ../VERITAS_ETH_R9_8_GROUPS_RUNS/cycle512.json

PYTHONPATH=src python3 -m veritas.research.parent_child_r98.general_cli \
  examples/r98_general_matching22.json --groups 65 \
  --output ../VERITAS_ETH_R9_8_GROUPS_RUNS/general65.json

PYTHONPATH=src python3 scripts/validate_r98_groups.py \
  --output ../VERITAS_ETH_R9_8_GROUPS_RUNS/validation.json
```

Reports include the configured finite count, fixed source count, full
structural preflight, actual child counts and sizes, crossing pairs, retained
modes, complete tuple counts, precision and execution ledgers. Failure reports
retain bounded preflight diagnostics when available. Large integer encoding
and creation-time residue inheritance are unchanged from the general driver.

Everything remains `FINITE_SCALED_EXPERIMENT`. Source padded packet bounds
fail on these finite singleton fixtures. Source qualification, universal
Python refinement, new general-driver Lean proofs, and asymptotic complexity
remain open. The saved traces still have no standalone independent recursive
trace consumer; runtime independent checks and fresh external execution are
the evidence boundary.

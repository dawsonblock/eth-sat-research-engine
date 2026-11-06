# Certified finite cycle transfer

This is a separate finite execution contract for singleton packet layouts.
The existing full weighted-tuple engines are unchanged: they continue to
enumerate every retained tuple, including structurally zero ones, or refuse
when their budget is insufficient. The transfer path aggregates that sum
algebraically and reports `global_tuple_stream_enumerated: false`.

## Identity and its conditions

Fix one point `T=t+4*zeta` at its prescribed precision `p_t=p+64M`. A real
singleton packet contains one Y row and one X column. A cross-group packet
has one nonzero mode Z at most: its target factor is affine in Z, and its
source form is X. Therefore every term with exponent `beta_Z >= 2` has an
identically zero target packet tensor. The verifier checks the singleton
packet, actual mode and endpoint conditions on every input; it does not
discard terms because of a work budget.

For k retained modes, `k <= M < p_t`. All binary exponent tuples are thus
inside the original weighted cutoff. The supported nonempty interaction
graph has exactly one simple cycle with at least three groups; groups without
crossing modes remain explicit. At a point with no nonzero modes, every
group is handled as an isolated group. Parallel modes, paths, multiple cycles
and non-leaf children currently refuse.

Each group child depends only on the modes incident to that group. For the
ordered cycle, let `A_i(a,b)` be the actual contraction of group i's child
when its preceding mode has exponent a and its following mode has exponent b;
all nonincident exponents in this representative are zero. Each value is
computed by constructing the immutable child, preserving its inherited
creation-precision tensor references, and contracting that child as a leaf.
Every child must have at most four edges and satisfy `r*M_child <= 6*M`.

The complete retained sum is the binary sum because all other exponents
vanish, and every binary tuple is within the cutoff:

```
sum_{beta >= 0, sum(beta) < p_t} product_g Z_g(beta)
  = sum_{beta in {0,1}^k} product_g Z_g(beta restricted to incident modes)
  =
product(isolated group contractions) * trace(A_0 * A_1 * ... * A_(k-1)).
```

All matrix arithmetic is exact in the point's extension ring. Isolated groups
are actually contracted; they are not assumed to equal one, since they may
contain scalar tensors. This is a finite cycle identity, not a proof of the
paper's source-regime recurrence or its complexity bound.

## Point certificate and independent verification

`evaluate_cycle_transfer` records all groups and every representative local
state. The point certificate includes each full serialized ChildGraph, its
ordered half-edge map, inherited references, packet recipes, creation
precision and calculated value. It binds the actual parent and layout.

`verify_transfer_certificate` independently reconstructs the mode basis and
each expected child without calling the production child constructor or the
production packet-entry evaluator. It checks every local contraction with
independent creation-precision arithmetic, sums the binary modes by separate
factor elimination, and compares against an independent half-edge point
calculation. The oracle can reject; it never supplies a production answer.
Passing this bounded checker does not prove universal Python refinement.

The current point path refuses if any actual child exceeds four edges. It
does not recursively use transfer to contract non-leaf children. At a single
point it also does not claim to have recovered the parent contraction.

## Complete grid and recovery

`contract_cycle_transfer` computes all `3M+1` residue-distinct interpolation
values at each of the two Hermite nodes, using the extension polynomial in
which the input tensors were originally created. It recovers the parent only
after every point has been independently certified, and compares the
coefficientwise exact rational recovery with a separate reference calculation.
An independent original-contraction calculation accepts or rejects the final
result and never supplies it.

The standalone full-grid checker replays every point certificate at its exact
expected node, extension coordinate and precision. It derives recovery rows
from those replays, recomputes the Hermite recovery and checks the claimed
result. Point certificates are compressed for storage; the consumer validates
canonical base64, single complete zlib streams, and both compressed and
cumulative uncompressed byte limits. The parent and layout must be provided
again for replay. Digests bind content; they are not signatures.

The explicit finite budget covers calls, work, cooperative time, precision,
factor width, and both serialized and decompressed evidence. Exhaustion
returns an inconclusive status with no result or completed certificate.
Work units charge the transfer and topology loops, but do not account for
every low-level JSON, compression, hashing or integer bit operation. The time
limit is cooperative, and hard peak memory is not enforced by this ledger.
The existing immutable ModeSet decoder has its own 20 MB record cap; an
explicitly larger total certificate budget does not override that limit.

## Examples

The 44-edge input is a connected cycle with nonconstant row and column
tensors. At `t=1, zeta=(1,0)`, it has 22 crossing modes and 130 actual local
child states. An independent 2x2 integer-matrix calculation provides an
additional point oracle. This example's degree-two extension is adequate for
the point test; it does not provide the 133 residue-distinct values per node
needed for its complete generic grid.

For a fresh degree-eight version with target precision 128, an independent
finite audit checked all 30 irreducible binary-coefficient degree-eight
polynomials. In the current certificate schema, repeated canonical W
coordinates alone require at least 110,235,136 uncompressed bytes over that
grid, before any other evidence. The default polynomial requires 135,883,264
bytes. Thus this schema cannot complete that example within the current
100,000,000-byte cumulative uncompressed cap. This does not rule out another
extension degree, an independently checked deduplicated schema, or a revised
explicit resource policy.

The audit also enumerated all 706 irreducible binary-coefficient polynomials
at the currently supported degrees eight through twelve. Under the same
133-point-per-node grid and serialized-child schema, the smallest lower bound
is 105,960,448 bytes. That finite audit does not cover different interpolation
grids, degrees beyond the implementation limit, or a deduplicated schema.

The 22-edge matching has a separately audited three-cycle in its **mode
interaction graph**; its original network is disconnected. Its tensors are
created directly in a degree-seven extension, with integer entries. The
complete grid has 67 values at each node, and the exact result is `17^22`.
The custom layout file is canonical JSON, binds the input parent digest, and
is independently audited when loaded.

The nonconstant 484-edge cycle with 512 groups has 242 crossing modes at
`t=1, zeta=(1,0)`. One such point requires 1,238 actual local child states
plus the point call, rather than enumerating the much larger weighted tuple
stream. This point does not establish a full 484-edge Hermite recovery.
For its full generic grid, a freshly created field of degree at least 11
would be needed. With the present requirement to compute each representative
child state at each point, the complete grid would require 3,599,083 actual
calls, exceeding the current 2,000,000-call policy ceiling. Evidence size and
work would also need to fit their own explicit caps.

From this checkout, use fresh external output paths:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r98.cycle_transfer_cli \
  examples/r98_transfer_cycle44.json --groups 64 \
  --output ../VERITAS_ETH_R9_8_TRANSFER_RUNS/point.json \
  --certificate ../VERITAS_ETH_R9_8_TRANSFER_RUNS/point.cert.json

PYTHONPATH=src python3 -m veritas.research.parent_child_r98.cycle_recovery_cli \
  examples/r98_transfer_mode_cycle22.json --groups 64 \
  --layout-file examples/r98_transfer_mode_cycle22_layout.json \
  --max-work 1000000000 --max-seconds 1200 --max-certificate-bytes 100000000 \
  --output ../VERITAS_ETH_R9_8_TRANSFER_RUNS/recovery.json \
  --certificate ../VERITAS_ETH_R9_8_TRANSFER_RUNS/recovery.cert.json

PYTHONPATH=src python3 scripts/validate_r98_cycle_transfer.py \
  --output ../VERITAS_ETH_R9_8_TRANSFER_RUNS/validation/report.json
```

Add `--verify` and use a new output-report path to independently replay the
existing certificate with the same input, layout and limits. New certificates
are never overwritten. The complete recovery example needs an explicit
evidence budget greater than the legacy 20 MB default. The validation script
also generates the nonconstant 484-edge input outside the checkout, computes
its point with 512 groups, and runs a fresh-process certificate replay.

Source recursion still fixes 64 groups and its source schedule. The finite
layouts here do not satisfy the source padded packet bound. No source
qualification, Lean proof of this new implementation, full connected-cycle
recovery, source-sized execution or asymptotic speedup is claimed.

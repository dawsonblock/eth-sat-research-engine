# General finite shrinking recursion

This development checkout adds `contract_general_shrinking`. The original
`contract_shrinking` remains the independently certified constant-row
specialization. `contract_scaled` remains the older depth-limited experiment,
and `contract_source` remains a separate, unqualified source admission path.

## What changes mathematically

For singleton packets with `a=u=1`, `L=2`, both real endpoints have the same
slot, and

```
W_xx(T) = -(T+2)(T+1)(T-1)/2.
```

The parent deformation has degree at most `3M`, regardless of its tensor
entries. General tensors require `3M+1` residue-distinct interpolation values
at EACH of `t=-1,+1`. The extension polynomial already attached to every
tensor is preserved. If its field is too small, the computation refuses;
the driver never relabels old coordinates as elements of a different field.

At a nonzero interpolation value, a cross-group singleton contributes its
`b=0`, weight-one mode whenever its Cauchy coefficient is nonzero. Every
positive `b` has zero source form because the tile quotient is zero. All
cross-group port pairs remain in the record. Zero modes are removed by this
identity; no retained weighted tuple is dropped for work-budget reasons.

The driver computes every admitted point by constructing all 64 children
for every retained tuple, checking `64*M_child <= 6*M` for all children before
recursing, and independently checking port maps, packet entries, one-tuple
coefficients and full half-edge point values. The only successful leaves
have at most four edges. Oracles accept or reject recursively computed
answers; they never supply replacement answers.

Full polynomial interpolation gives the required jets. Exact rational
Hermite recovery checks each coefficient's precision using a separate
functional and recovery implementation. For these scaled parameters,
`q_t=3M` and `p_t=p+64M`. The driver makes no constant-row assumption and
does not infer degree from agreement at sampled values.

## Runnable nonconstant validation

`examples/r98_general_matching22.json` has 22 matching edges, row entries
`[2,3]`, column entries `[5,7]`, target precision 128, and extension degree 7.
Its independent closed-form deformation is

```
F(T) = (24 + 7*W_xx(T))^22,  degree(F)=66,
F(0) = 31^22.
```

The run uses 67 interpolation values at each node, 134 complete point
evaluations, 8,577 actual recursive invocations, and children of size zero
or two. Point precision is 1,536 bits. The nonconstant point values exercise
full polynomial recovery. This example has no cross-group modes; separate
point tests exercise nonzero cross-group modes and complete weighted streams.
It is one active general level. A nonconstant two-active-level run has not
been established by this validation.

From this checkout, write new evidence outside it:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r98.general_cli \
  examples/r98_general_matching22.json \
  --output ../VERITAS_ETH_R9_8_GENERAL_RUNS/matching22.json

PYTHONPATH=src python3 scripts/validate_r98_general.py \
  --output ../VERITAS_ETH_R9_8_GENERAL_RUNS/validation.json
```

The CLI accepts an explicit `--max-points` up to 4,096 and input extension
degree up to 12. Its default point cap is 256. Other precision, factor,
arity, recipe, work, time, call and evidence limits remain bounded. These
are admission ceilings, not promises that every input below them succeeds.
In particular, a positive-precision 1,024-edge active call needs more than
65,536 bits at its first point and is refused by that precision cap.
At recursive depth k the cumulative precision is
`p_root + 64*(M_0 + ... + M_(k-1))`.

## Bounded large coefficient encoding

Decimal integer encodings still have the existing 400-character limit.
Nonnegative integers at least `10^400` use the reserved canonical object
`{"$veritas_uint_hex":"<minimal lowercase hex>"}`, with at most 65,536 bits
and narrower creation-ring bounds. Small integer bytes remain unchanged.
Malformed, oversized, padded, uppercase and unnecessary small-value tags
are rejected. Production and independent entry decoders validate this
representation separately. Creation precision still determines the entry
residue BEFORE its canonical coordinates are lifted to a higher precision.

Reports contain ordinary elapsed-time floats and may contain tagged large
point coordinates. Ordinary JSON consumers can inspect metadata directly;
numeric consumers must decode the documented integer tags. The strict
immutable-record decoder is not a parser for an entire timing report.

## Why the generic connected 484-edge case still refuses

The existing deterministic cycle layout has 22 cross-group singleton
packets. At `zeta=1`, each yields a weight-one mode. For root precision 512,
the point precision is 31,488, and the complete tuple stream has

```
binomial(31488 + 22 - 1, 22)
  = 815850175190636934649750123028157781189945808220074601499347351018552747446400
```

members, about `8.16e77`, at that point alone. Its generic grid needs 1,453
values per node and extension degree at least 11. Raising wire and precision
caps does not remove this complete-enumeration cost. The existing degree-two
constant-row cycle fixture is evaluated by the original specialized driver;
this general driver does not silently switch algorithms.

Making this connected general computation practical requires a justified
change in how the complete sum is evaluated, or source-eligible packet and
schedule constructions. Discarding structurally zero tuples, using the
oracle's value, or declaring sampled points constant would violate the
current execution contract. The sparse coefficient oracle only bounds
exponents for a requested coefficient; it never changes the tuple stream.

## Qualification

All new executions are `FINITE_SCALED_EXPERIMENT`. The source's padded
packet bound fails on these singleton fixtures. Source qualification,
universal Python refinement, source-active execution, and asymptotic
bit-time/peak-space bounds remain unestablished. The existing Lean modules
are regression checked; no new general-driver refinement theorem is claimed.
The source schedule needs `ceil(log2(s)) >= 131072` even to obtain positive
`u_0`; raising the finite wire ceiling cannot establish that regime.
Saved general traces have no standalone independent recursive-trace
certificate consumer yet; runtime checks and fresh external execution are
the executable evidence boundary.

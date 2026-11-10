# R9.12 implementation

This revision extends the recursive numerical path. It does not implement or
qualify the complete manuscript-active algorithm. The pinned manuscript is
unchanged. The distribution version is `3.8.2.post912`.

## Implemented mathematical operations

`ParentCall` and every generated `ChildGraph` carry the truncation length ell.
Every inherited recipe retains its creation precision. Generated packet recipes,
leaf products, parent term products, independent leaf elimination and recovered
results all live in `(Z/2^P Z)[U]/(f(U))[V]/(V^ell)`. The explicit implementation
limit is 1 <= ell <= 64. Empty children retain ell and return the correct ring
unit. Scalar records omit the new field, preserving historical canonical bytes.

The Cauchy kernel is scalar in V. Its coefficients are embedded with zero higher
V coefficients. Inherited tensor entries may have arbitrary canonical extension
coordinates in every V coefficient. Multiplication is truncated convolution;
reconstruction applies the rational Hermite functional to each coordinate.
No evaluation at a V value, or division by V, is used.

For each explicit finite pair (a,u), `Recovery` derives the nodes and their
multiplicities and precisions from `hermite_parameters`:

- L = 2^a, alpha = 2L, h = ceil(3M/u).
- Active nodes t are nonzero integers in [-L,L) with i = v2(t) < u.
- q_t = h(u-i), D_t = L/2^i, P_t = P + 8hD_t + 8M(a+1).

This instantiates `lem:tapered-hermite` for bounded inputs. The current finite
parameter limit remains 1 <= u <= a <= 3. The polynomial degree bound is
`(2L-1)b`, where b counts ports on independently checked nonconstant row tensors.
Only the provably zero coefficient tail is omitted. The original q_t, P_t and
functional are retained. Each functional is checked on every monomial through
the certified degree; each weight's denominator loss is checked against P_t.

The producer forms the general functional through reciprocal factors. The
consumer independently multiplies the complementary polynomial E_t and inverts
its series by a coefficient recurrence. The producer and consumer use different
interpolation recurrences and separately implemented extension arithmetic.
The checker still shares higher-level support orchestration; this is finite
independent replay, not formal executable refinement.

## Evidence transport and arithmetic

Each point stores a local coefficient array once, addressed by its SHA-256.
Original and folded port records reference that table. The independent reader
checks hashes, exact membership, missing and unused definitions, and expansion
limits, then reconstructs the original records for mathematical verification.

Large records additionally use a bounded zlib/base64 envelope, with exact decoded
length and a content digest. The reader rejects altered hashes, invalid framing,
trailing data, nested compressed envelopes and excessive expansion. Mathematical
checks operate on reconstructed records. Plain and compressed numerical streams
are compared byte-for-byte after expansion in regression tests.

The stream chain hashes actual transported records. The total stream budget is
separate from the 20 MB compressed-record expansion cap and the explicit result
cache budget. New runs may request up to 1 GB of stream data. This does not
constitute a polynomial-space argument or an OS memory ceiling.

Profiling identified repeated decoding/digest work and full-width integer
remainders. Immutable records cache their digests and decoded views; public
views are fresh deep copies. Lowercase hexadecimal validation uses a compiled
exact character check. Multiplication modulo 2^P uses the identity
`x mod 2^P = x & (2^P-1)`, including negative intermediate coefficients.
Producer Hensel inversion doubles its actual working precision at each step.
Tests compare high-precision products and inverses against separate polynomial
arithmetic, including a reference retaining ordinary integer remainder.

## Interface

```
PYTHONPATH=src python -m veritas.research.parent_child_r912.cli INPUT.json \
  --schedule 2:2,1:1 --output-dir /absolute/external/run
```

The CLI accepts the canonical integer-network input or a canonical
`ParentCall.record()` containing full creation-time jet recipes. Field capacity
must accommodate the certified interpolation degree. The default finite packer
repeats balanced whole-vertex labels across coordinates, then checks actual
loads. It does not establish the manuscript's padded-packet count. A layout or
resource refusal returns no contraction result. Successful CLI executions are
always independently replayed. A replay can be requested with `--replay-dir`.

The coupled-cycle driver retains its explicitly authenticated shifted root
layout and component-preserving descendant layout:

```
PYTHONPATH=src python scripts/experiment_r911.py --compact --compress-records \
  --output-dir /absolute/external/coupled484 \
  --max-work 2000000000 --max-seconds 3600 --oracle-max-work 100000000 \
  --cache-bytes 8000000 --max-certificate-bytes 1000000000
```

This fixture has a rank-two interacting core and constant padding. Its direct
integer transfer-trace reference does not substitute for any recursive result.
A complete run and replay must finish before its connected two-level gate passes.

`experiment_r912_interaction.py` generates fully nonconstant degree-three
networks. Its separate integer variable-elimination reference records an
observed frontier, not a lower bound on treewidth. Small instances are checked
against exhaustive enumeration. Resource-limited recursive runs remain
inconclusive even when the independent oracle supplies an exact reference.
The separately classified exact elimination route and the 2^96 support
diagnosis are described in `R912_EXACT_ELIMINATION_ROUTE.md`.

## Outstanding manuscript obligations

The exact source schedule `u_d=floor(lambda/(131072*2^d))`,
`a_d=2*sum(u_0,...,u_d)`, source-sized packing, complete source mode-count bounds,
source-recursive closure and the source leaf rule are not connected to a
qualified general executor. A finite (2,2) test is not an instance of that
schedule. General CNF/density reductions, complete bit-operation accounting,
polynomial-space and subexponential-time proofs, and Python-to-Lean refinement
remain open. Charged work units, stream bytes and process RSS must be reported
separately; `bit_operations` remains null.

# R9.2 packet-address implementation slice

## Status

This change implements and checks the canonical global packet address for
bounded finite instances. It also adds a Lean model of canonical pattern,
orientation, copy, and slot-word conversion. It does **not** close the full
R9.2 acceptance gate: the scalar class offset to copy-bit word conversion is
not yet proved in Lean together with the actual edge builder, and the Python
implementation has only bounded exhaustive validation.

The theorem branch remains disabled. This work does not establish universal
packing, child contraction, recursion, complexity, or executable refinement.

## Address convention

For a width-`a` directed class `(row, column)`, define the coordinate pattern
`P[i]=(min(row[i],column[i]), max(row[i],column[i]))`. Let `q` be the number
of equal coordinates and `c=2^q`. For a padded class offset `k`, set
`packet, copy = divmod(k,c)`. In the integer slot word, coordinate bit `i`
is the row/column orientation bit when the pattern symbols differ; when they
are equal, it is copy bit `rank(i)` among equal coordinates in increasing
coordinate order.

The inverse reads unequal-coordinate bits as orientations, reads equal-
coordinate bits as the copy word, and reconstructs `k=packet*c+copy`. Row and
column symbol words remain ordered and side-tagged; equal numeric symbols do
not merge the row endpoint with the column endpoint. Each input edge has an
occurrence ID, so repeated edges receive distinct offsets.

## Code and proof mapping

* `src/veritas/research/eth_packing_v26/packet_bijection.py` defines the
  immutable address, encoder, decoder, and edge-occurrence lookup.
  `implicit.py` now routes `ImplicitPacking.packet_slot`, dense packet
  materialization, and sparse active packet materialization through this
  codec, so the bounded checker audits the representation used by the finite
  builder instead of a disconnected address helper.
* `packet_bijection_check.py` independently enumerates the directed-class
  domain and the pattern/packet/slot codomain. It checks injectivity,
  surjectivity, inverse equations, cardinality, and real-edge correspondence
  with the emitted sparse packet builder. It returns
  `INCONCLUSIVE_RESOURCE_LIMIT` before exceeding its configured address/edge
  limits.
* `proofs/D3GlobalPacketAddress.lean` proves inverse laws for the canonical
  pattern-plus-copy/orientation interleaving and proves that each directed
  list of symbol pairs reconstructs from its unordered pattern and unequal
  coordinate orientations. The prior `D3PacketBijection.lean` separately
  proves natural-number quotient/remainder round trips.
* `scripts/validate_conditional_expectation_lean.py` now compiles 23 pinned
  modules and checks the new exact theorem names and their axiom reports.
  The recorded gate leaves `lean_full_padded_offset_to_global_address_proven`
  and `lean_python_builder_refinement_proven` false.

## Validation

The focused finite command is:

```bash
PYTHONPATH=src python -m pytest -q -o addopts='' \
  tests/test_r92_global_packet_bijection.py \
  tests/test_d3_implicit.py \
  tests/test_sparse_packet_source_equivalence.py
```

The recorded result is 53 passed. The Lean gate command is:

```bash
python scripts/validate_conditional_expectation_lean.py \
  --output validation/r9_2_packet_lean.json
```

That gate passed on Lean 4.35.0 with 23 modules. It records kernel checking
for the new model statements but does not upgrade any universal theorem or
source-to-executable claim.

## Remaining R9.2 obligations

1. Prove a `Fin`-indexed binary-word/value equivalence and compose it with the
   existing `offset = packet*c + copy` quotient/remainder theorem.
2. Formalize the complete finite types for all directed symbol classes and
   canonical unordered patterns, including class and padding cardinalities.
3. Prove that each edge occurrence in the actual deterministic constructor
   maps to the address specified by the Lean functions. This requires a
   verified source correspondence or an equivalent executable refinement
   argument; finite differential tests alone do not suffice.
4. Only after those proofs, proceed to R9.3 all-mode contraction and recursive
   Hermite recovery. The present checker is not a substitute for those stages.

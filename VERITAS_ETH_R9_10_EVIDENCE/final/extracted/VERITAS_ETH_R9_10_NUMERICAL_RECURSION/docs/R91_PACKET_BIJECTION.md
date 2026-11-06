# R9.1 packet slot bijection

`lem:tensor-packets` pads every directed class to a common multiple `H` of
`L = 2^a`. `proofs/D3PacketBijection.lean` formalises the resulting address
space and proves it is a bijection.

## Domains

* A directed class is an element of `allWordPairs r a`, i.e. a pair of label
  words. There are `r^(2*a)` of them.
* A padded slot is `(class, offset)` with `offset < H`.
* A packet position is `(class, packet, copy)` with `packet < H / L` and
  `copy < L`.

## Encoding

```
encodeOffset L offset      = (offset / L, offset % L)
decodeOffset L packet copy = L * packet + copy
```

## Proved

* `encode_copy_bounded` — the copy index is below `L`.
* `decode_encode` — decoding an encoded offset returns the offset.
* `encode_decode` — encoding a decoded position returns the position
  (requires `0 < L` and `copy < L`).
* `encode_injective` — the encoding is injective.
* `decode_surjective` — every offset below `packets * L` is the image of a
  packet position inside the bounds.
* `packet_capacity` — a packet holds exactly `L` slots.
* `slot_packet_count` — `r^(2*a) * H = r^(2*a) * (H / L) * L` when `L ∣ H`.
* `packet_count_exact` — `(H / L) * L = H` when `L ∣ H`.
* `empty_class_still_padded` — a class with zero observed load still owns its
  padded block, so the map is total on empty classes.
* `packet_positions_distinct` — distinct positions decode to distinct slots.
* `d3_edge_slot_accounting` — the `M` edges occupy exactly `M` of the
  `D_arr * H_pad` padded slots, `M <= D_arr * H_pad`, and the slots regroup
  into `D_arr * (H_pad / L)` packets of `L` slots.
* Three kernel-checked fixtures, including `L = 2`, `H = 6` giving
  `[[0,1],[2,3],[4,5]]`.

## Not proved

* The edge-to-class assignment is now accounted for at the level of counts
  (`d3_edge_slot_accounting`), but the explicit injection
  `edge -> (class, index within class)` is not formalised as a function.
* Orientation of unequal symbol pairs uses `d3DecodeSymbolPair` from
  `D3SlotSplit.lean`; the roundtrip is proved there, but the composition with
  the packet address is not.
* The manuscript's recursive child construction, creation-time precision, and
  termination are untouched.

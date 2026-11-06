# R9.6 exact ring contract

This document fixes the arithmetic that every R9.6 component assumes.  It is a
*contract*: the code is checked against it, not derived from it.

## 1. The creation ring

```
R_pc  =  (Z / 2^pc Z)[U] / (f(U))          pc = creation precision, 1 <= pc <= 1024
f     =  a monic integer polynomial given by its binary coefficient vector
deg f =  e,  1 <= e <= 64 (SourceLimits / EntryLimits caps)
```

* **Representatives.**  An element of `R_pc` is a tuple `(a_0, ..., a_{e-1})`
  of integers with `0 <= a_i < 2^pc`.  The representative is canonical: there
  is exactly one tuple per residue class, so `==` on tuples is equality in the
  ring.  No signed or balanced representation is ever used.
* **Irreducibility.**  `f` must be irreducible over `GF(2)`.  `R_pc` is then a
  finite local ring with residue field `GF(2^e)`, not a field when `pc > 1`.
* **Units.**  `a` is a unit iff its mod-2 reduction is nonzero.  Inverses are
  computed by Hensel/Newton doubling and verified by `a * a^{-1} == 1`.
* **Reduction.**  `U^e == -sum_{i<e} f_i U^i`.  Multiplication reduces the
  product polynomial by that relation, coefficient-wise modulo `2^pc`.
* **Valuation.**  `valuation(0) = pc`; otherwise the minimum 2-adic valuation
  of the coordinates.

## 2. The truncated jet extension

```
J_{pc,ell}  =  R_pc[z] / (z^ell)
```

* An element is a tuple of `ell` ring elements `(b_0, ..., b_{ell-1})`,
  `1 <= ell <= 64`.
* Multiplication truncates at `z^ell`.  This is an exact quotient of a
  polynomial ring, not a floating approximation.
* `J` is **not** a field and `inverse` requires `b_0` to be a unit in `R_pc`.

## 3. Capture at `pc`, use at `P >= pc`

`CreationJetEntry.capture(ring_at_pc, value)` stores the canonical
representatives together with `pc`, `f` and `ell`.  Later use at a larger
precision `P` **re-lifts the same integer representatives** and does *not*
recompute the formula at `P`.

This is deliberate and it is a documented non-homomorphism: the canonical
integer representative map

```
lift : R_pc -> R_P ,   (a_i) |-> (a_i mod 2^P)
```

is additive and multiplicative on representatives but **not** a ring
homomorphism in the sense of commuting with reduction, because `2^P` arithmetic
and `2^pc` arithmetic differ.  Concretely, `lift(x + y) == lift(x) + lift(y)`
holds for the stored representatives, but `lift(x * y)` need not equal
`lift(x) * lift(y)` when a reduction carried information above `2^pc`.  Two
properties are therefore enforced in code and tested:

1. an entry is **always** evaluated at its creation precision first;
2. the result is captured and lifted, never recomputed at the target precision.

`SourceNode` additionally enforces `initial_precision <= tensor.creation_precision
<= node.precision`, so a node can never evaluate a tensor below its creation
precision.

## 4. Packet coefficient semantics

A packet payload is `[rows, cols, local, targets, sources]`.

* `rows` and `cols` partition the packet's ports.
* `local[i][j]` is a creation-ring jet for row `i`, column `j`.
* `targets` is a list of `[beta, coefficients_per_row]`; `beta` is a formal
  mode exponent.  Targets with `beta == 0` are omitted from coefficient
  extraction (each row factor is affine and only nonnegative exponents occur,
  so a zero exponent contributes only through the constant term).
* `sources` is a list of `[beta, integer_coefficients_per_column]`.

For a Boolean index `bits`, with `l_i = sum_{j : bits[col_j]} local[i][j]`:

```
constant_i  =  l_i           if bits[row_i] else 1 - l_i
linear_i[m] =  coeff_m[i]    if bits[row_i] else -coeff_m[i]
value       =  [ prod_i (constant_i + sum_m linear_i[m] z_m) ]  at z^beta
               * prod_s ( sum_{j : bits[col_j]} source_s[j] )^{beta_s}
```

The bracket is a truncated polynomial coefficient over `J_{pc,ell}`.

## 5. What a hash proves

Every digest in this release is a **domain-separated SHA-256 of a canonical
encoding**.  It proves *byte identity of that encoding*.  It does not prove
provenance, authorship, mathematical correctness, approval, or the freshness of
any external artifact.  Every digest record says so in a `does_not_prove` list.

## 6. What is deliberately absent

* No floating-point path exists anywhere in the exact arithmetic.  `parse_float`
  in the recipe decoder raises.
* No silent precision reduction: `reduce_precision` requires an explicit lower
  precision and `lift` refuses to decrease.
* No division by a non-unit and no inversion of an even denominator.

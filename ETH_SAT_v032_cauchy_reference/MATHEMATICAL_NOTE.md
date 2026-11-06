# Local Cauchy deformation: exact identities and boundary

Fix packet size `L >= 1`, set

```text
S = {-L, -L+1, ..., L-1}
C(T) = product_{t in S}(T-t)
W_xy(T) = C(T) / (C'(0) * (T-(y-x))),  0 <= x,y < L.
```

Since `y-x` lies in `S`, polynomial division by `T-(y-x)` has zero
remainder. Thus every `W_xy` is a rational-coefficient polynomial of degree
`2L-1`; the denominator is the nonzero constant `C'(0)`. In particular,

```text
C'(0) = (-1)^(L-1) L! (L-1)!.
```

At `T=0`, the diagonal entry is the derivative value
`C'(0)/C'(0)=1`; every off-diagonal entry has numerator `C(0)=0` and a
nonzero denominator. Hence `W(0)=I`.

At a grid node `s in S`, the entry is zero unless `y-x=s`. On that one
diagonal it equals `C'(s)/C'(0)`, by the factor theorem. Therefore each
sample matrix is a scalar multiple of a shift matrix (or zero if that shift
does not occur within the packet). This is an exact local sparsity property.

For arbitrary row and column tensors `A(Y)` and `B(X)`, define

```text
F(T) = sum_{X,Y in {0,1}^L} A(Y) B(X)
       product_x l_{Y_x}((W(T)X)_x),
l_0(z)=1-z, l_1(z)=z.
```

At `T=0`, `W(0)X=X` is Boolean, and the product of the `l` factors is 1
exactly when `Y=X`, otherwise 0. Consequently

```text
F(0) = sum_{X in {0,1}^L} A(X) B(X),
```

which is the original equality-wire contraction. The implementation checks
this identity on small exact integer tables.

## Local 2-adic mode check

When `L=2^a`, the grid `S` is a full residue system modulo
`alpha=2^(a+1)`. For each `t` in `S`, the polynomial matrix
`W(t+alpha*z)` has coefficients in `Z_(2)`, the rationals with odd
denominator. This does not mean its coefficients must be ordinary integers;
odd denominators are units modulo every `2^p`.

For an active node with `i=v_2(t)<a`, put `h=2^(i+1)` and divide a column
tile into `y=y0+h*j`. For a row/tile pair satisfying
`v_2(t-y0+x)<=i`, set `d=T-y0+x`. Then

```text
W_xy(T) = (C(T)/(C'(0)*d)) * sum_{b>=0} (h*j/d)^b.
```

The ratio has 2-adic valuation at least one. The first factor has valuation
at least `a+1-i`, hence at least one. The term indexed by `b` is therefore
divisible by `2^(b+1)`. Modulo `2^p`, terms with `b+1>=p` vanish exactly.
The code checks this equality for individual crossings, finite integer local
coordinates, and small precisions. It is a direct local check of the paper's
geometric expansion; it does not verify global mode factorization or the
count of all retained mode tuples.

The prototype also has a two-group single-packet evaluator. It assigns row
and column slots by the `i`th orientation bit, creates tile modes with
weights `b+1`, enumerates tuples with total weight below `p`, and compares the
sum of products of the two independently contracted group values against a
direct evaluation of `F(T)` modulo `2^p`. Sixteen seeded small cases pass.
This demonstrates the algebraic factorization for that tiny layout. It does
not implement the manuscript's deterministic packet-packing lemma, the
64-group child construction, or its `3M/32` edge bound.

These identities establish only the local deformation and its value at zero.
They do not prove the tapered Hermite interpolation precisions, the global
factorization of modes into smaller networks, the bound on all surviving
mode tuples, or the total recursive bit/time/space complexity. In
particular, `W(0)=I` alone cannot justify discarding any Taylor terms or
claiming a subexponential contraction.

## Tapered Hermite recovery reference

The companion `tapered_hermite.py` now implements the interpolation step
from the manuscript's tapered-Hermite lemma for a finite free module whose
coordinates are represented by integers modulo powers of two. Let
`L=2^a`, `1 <= u <= a`, `M >= u`, and
`h=ceil(3M/u)`. For each nonzero grid point `t`, the code sets

```text
i = v2(t)
q_t = h * max(0, u-i)
D_t = L / 2^i
p_t = p + 8*h*D_t + 8*M*(a+1).
```

Only nodes with `q_t > 0` are active, and only the first `q_t` coefficients
of the local jet `F(t + 2^(a+1) z)` are requested. The code constructs

```text
E_t(T) = product over q in S\{0,t} of ((T-q)/(t-q))^q_q
```

and evaluates the formula

```text
F(0) = sum over active t of
       E_t(0) * ([F(t+alpha*z) / E_t(t+alpha*z)]_{<q_t})(-t/alpha).
```

The local factor `E_t(t+alpha*z)` has constant coefficient one and
2-adically integral coefficients, so its truncated reciprocal can be
computed without losing precision. The resulting rational terms are summed
exactly before reduction modulo `2^p`; the code rejects nonintegral final
coordinates. This implements the lemma's precision schedule and recovery
formula, rather than approximating it with equal precision at every node.

Validation differentially reconstructs 25 seeded integer-vector
polynomials of degree at most `M*(2L-1)`, including packet size `L=16`, and
exhaustively checks all 81 integer scalar polynomials of degree at most three
for `L=2`. The largest local precision in the seeded run was 1,093 bits.
These checks support the implementation on those inputs. The interpolation
lemma's general validity comes from its proof in the cited manuscript, not
from finite testing.

The implementation remains narrower than the theorem's coefficient ring
`(Z_(2)[U]/(f))[V]/(V^ell)`: it handles coordinate vectors under rational
scalar multipliers, but does not implement multiplication in that full
algebra or the manuscript's interpolation over lifted residue-field
elements. It also does not construct all packet children, recurse over the
complete mode set, or establish global bit, time, or space bounds. The
subexponential runtime is therefore not verified by this reference.

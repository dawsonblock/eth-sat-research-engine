# Geometric point-mode identity and valuation

This note proves the local point identity under the packet orientation and
unramified-ring hypotheses. It does not prove that the implementation
constructs theorem-scale packings or satisfies the full runtime bound.

Let `L=2^a`, `alpha=2^(a+1)`, `S={-L,...,L-1}` and
`C(T)=product_(q in S)(T-q)`. Let `t` be nonzero in `S`, with `i=v2(t)<a`,
and let `zeta` be integral in the unramified extension. For a cross-group
row slot `x` and column tile `y=y0+2^(i+1)j`, packet orientation says that
bit `i` of `x` equals bit `i` of `y0`. Hence
`d=t-y0+x` is nonzero and `v2(d)<=i`: either the lower `i` bits of `x`
and `y0` differ, giving a smaller valuation, or they agree and the `i`th
bit of `t` gives valuation exactly `i`.

Write `T=t+alpha*zeta`, `q=y0-x`, and `v=v2(t-q)`. Since `S` is a
complete residue system modulo `alpha`, the nonzero differences from any
`t in S` have the same multiset of 2-adic valuations. Thus
`v2(C'(t))=v2(C'(0))`. Every factor
`t-q'+alpha*zeta`, for `q' != t`, has valuation `v2(t-q') <= a` because
the added term is divisible by `2^(a+1)`. Omitting the factor for `q`, the
remaining factor `T-t` has valuation at least `a+1`. Consequently

\[
v_2\!\left(\frac{C(T)}{C'(0)(T-q)}\right)
\ge a+1-v \ge a+1-i \ge 1.
\]

The ratio `rho=2^(i+1)/(T-q)` is integral with valuation at least one:
cancel the explicit factor `2^v` first and invert only the remaining odd
unit. With `y=y0+2^(i+1)j`, the geometric identity gives

\[
W_{xy}(T)=W_{x,y_0}(T)\sum_{b\ge0}(\rho j)^b.
\]

The coefficient of `j^b` has valuation at least `b+1`. The remainder after
terms `b=0,...,p-2` has valuation at least `p`, since `1-rho*j` is a unit;
it therefore vanishes modulo `2^p`. This also covers `j=0`, using
`j^0=1`. Products of these mode coefficients inherit the sum of their
weights, so any monomial with total weight at least `p` vanishes.

The finite `make_point_modes` implementation factors the denominator in
this way and checks each generated coefficient's valuation. Its checker
also reconstructs each small Cauchy matrix entry directly. Those finite
checks are implementation evidence; the argument above is conditional on
the stated orientation and ring hypotheses and is not a proof of the
recursive schedule or complexity bounds.

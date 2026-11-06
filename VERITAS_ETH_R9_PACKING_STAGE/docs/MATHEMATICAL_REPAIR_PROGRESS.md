# Finite mathematical repair: actual children and source Hermite recovery

The reference ZIP described in the request was unavailable. These checks were
implemented against the vendored 25 October preprint, independently of that
unavailable code. They do not establish theorem-mode eligibility.

## Actual packet recipes and port loads

`child_recipe_check.verify_constructed_child_recipes` checks one supplied
constructed tuple after the packing source and point-mode certificate have
been validated. It first checks the complete half-wire partition. It then
indexes the checked local Cauchy coefficients and modes independently of the
child builder and checks every packet recipe's local rows, target coefficients,
source linear forms, exponents, and creation ring. It measures actual `Y` and
`X` packet ports for each child group. In the strict finite policy, a group
whose row or column load exceeds `3M/r` causes an inconclusive result before
child execution. The verifier checks a supplied finite construction; it does
not prove the deterministic packing lemma, theorem-size hypotheses, or the
identity for all inputs.

`RecursionPolicy(verify_tuple_identities=True)` independently enumerates
parent half-wire assignments and affine row selections for each tuple emitted
by the finite structural enumerator, including Hall-pruned terms. It compares
the result with the recursively contracted child product and fails without a
count if they disagree. The oracle is limited to three active parent wires and
shares the checked mode certificate and exact ring arithmetic. It does not by
itself prove that the structural enumerator omitted only zero terms. The
point-level half-wire check runs automatically for active calls of at most two
wires, and can be explicitly requested at larger supported calls. It can be used
together with the tuple check. Oracle event counts and observed work are recorded; source
validation, big-integer costs and memory allocation are not fully metered.

## Source-prescribed Hermite formula

`eth_interpolation.source_hermite` implements `eq:tensor-hermite-origin`
directly. It forms all active nodes with `q_t=h max(0,u-v_2(t))`, builds
`1/E_t(t+alpha*z)` as a truncated exact rational series, and applies all
source-node terms at `-t/alpha`. It checks each coefficient's required
precision using the two-adic valuation of its recovery weight and never
inverts an even denominator modulo a power of two. Coefficients beyond the
known polynomial degree are identically zero and need not be transmitted.
The finite recursor uses this formula, validates its generated functional
against all monomials up to the degree bound, and fails closed on corrupted
weights or insufficient precision.

The public older prefix-reconstruction API now also validates its plan before
use. Previously, changing a recovery weight could make it return 6 instead
of 19 for a constant polynomial 19. Its existing monomial validator detects
the corruption and reconstruction now invokes that validator.

`tests/test_source_hermite_formula.py` checks the complete formula using an
independent rational implementation based on repeated linear-series division,
random odd-denominator polynomials, per-coefficient precision boundaries and
forged plans. `hermite_crt.py` supplies a distinct bounded generic CRT
reference, checked against the existing dense confluent solve. These finite
references use explicit degree, node, precision and term caps; they are not the
paper's uniform proof of `p_t` sufficiency, polynomial-space implementation,
or a complete bit-work analysis.

## Reproduction and status

```sh
PYTHONPATH=src python -m pytest -o addopts= -q \
  tests/test_source_hermite_formula.py tests/test_hermite_crt_reference.py \
  tests/test_tapered_reconstruction_fail_closed.py tests/test_child_recipe_independent.py
```

The theorem branch remains `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.
The explicit 64-wire model is far below the active packing regime; the general
packing construction, universal child identity and shrink proof, unbounded
arithmetic/description path, complete complexity ledger, independent proof
review and arbitrary-density reduction remain open. Finite tests do not
upgrade these obligations to verified claims.

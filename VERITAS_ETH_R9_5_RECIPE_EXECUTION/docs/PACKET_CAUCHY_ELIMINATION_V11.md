# v1.1 mathematical audit: finite packet search + exact polynomial factor elimination

## Scope

This release is **not a reproduction of the paper's collision-packing theorem, two-adic weighted symbol-group factorization, or subexponential recursive tensor contraction**. It adds two exact small-instance tools, both amenable to independent checking.

## A. Deterministic finite packet optimizer

For a permutation `order` mapping new wire slots to old wire identities, assign slot `i` to packet `floor(i/L)`. For each factor `f`, let `d(f,p)` be its number of incident wires assigned to packet `p`. Define

    score(order) = sum_f sum_p (d(f,p) choose 2).

`plan_packets` minimizes this *surrogate same-factor incidence collision score*. For <=8 wires it enumerates every permutation if its explicit budget and deadline allow completion; only then does `exact_optimum=True` certify optimality **for this surrogate objective**. For 9–16 wires it performs deterministic improving swaps, without global optimality.

`relabel_network` rewrites port identifiers while preserving each factor's local port-bit order and truth table. This is a literal graph isomorphism: a bijection between assignments to old and new wires, so exact contractions match. Tests check this against independent brute-force enumeration and ordinary variable elimination. Different permutations can produce different **intermediate deformed polynomials** at nonzero interpolation points; only the value at T=0 is invariant.

These factor-incidence collisions are **not** the source manuscript's packet collisions. No quantitative D.3 distribution, bounded-collision schedule, or recursive wire-budget theorem is inferred.

## B. Exact Cauchy jet using factor graph elimination

Let there be M original wires. Split each wire into one row half-edge bit `Y_i` and one column half-edge bit `X_i`. At a permitted node `t`, packet size `L`, and local coordinate `T=t+2L z`, define

    K_i(X,z) = sum_{j in packet(i)} W_ij(t+2L z) X_j.

Here W is the exact rational local Cauchy kernel already implemented in v0.8. The transformed contraction is

    F(t+2L z) = sum_{X,Y in {0,1}^M} A(Y) B(X)
                    product_i [Y_i K_i(X,z) + (1-Y_i)(1-K_i(X,z))].

The implementation evaluates this expression over the finite commutative ring

    (Z / 2^p Z)[z]/(z^K)

where shifted Cauchy coefficients have **odd denominators** and therefore have exact modular inverses. An internal factor represents each row/column tensor and each local Cauchy kernel. Eliminating each binary half-edge variable is a sum-product operation. It preserves the contraction exactly over this ring by distributivity.

At each elimination step, all factors involving the selected half-edge bit are multiplied; the bit is summed over {0,1}; a new polynomial factor is constructed over the other variables in that bucket. This uses exact modular convolution and no numerical approximations. It may avoid enumerating all 4^M pairs of half-edge assignments, but table sizes can still grow exponentially with induced elimination width; this is **not** the specialized paper recursion or a subexponential algorithm.

## C. Hard limits and evidence

- <=12 original wires; packet sizes 1,2,4,8; node in {-L,...,L-1}; <=128 precision bits; <=24 jet coefficients.
- Explicit factor-table and total-table caps, 30-second maximum timeout; exhaustion yields `UNKNOWN` in the API.
- Optional packet optimization permutes the *network* before deformation; comparing to a reference oracle must use the same permutation.
- For <=6 wires, the API's `cross_check=true` computes the jet a second way using the old independent exhaustive half-edge calculation. Results are marked `RESEARCH_CROSS_CHECKED` only after exact residue agreement.
- A nonzero-node jet is **not** the original #SAT count. At node 0, coefficient 0 of F(2Lz) equals the original count mod 2^p.
- No independent proof of asymptotic complexity has been executed, and runtime benchmarks on tiny examples cannot justify a large-input speed claim.

## D. Reproduction

    PYTHONPATH=src python -m pytest
    PYTHONPATH=src python scripts/validate_v11.py
    PYTHONPATH=src python benchmarks/v11_cauchy.py
    PYTHONPATH=src python -m veritas.cli cnf examples/example.cnf --packet-schedule
    PYTHONPATH=src python -m veritas.cli cnf examples/example.cnf --cauchy-eliminate --packet-size 2 --node 1 --jet-order 4 --precision-bits 12

### API

`POST /v1/research/packet-schedule` and `POST /v1/research/cauchy-eliminate`. See local `/docs` for typed request models and JSON evidence. Experimental algorithms never become production verifiers by inference.

## E. Source

OpenAI's October 25, 2026 manuscript, in particular its Cauchy construction and tensor contraction appendix, as linked in `docs/PAPER_TO_CODE_MAP.md`. The paper's claimed asymptotic algorithm requires additional ingredients not present in v1.1.

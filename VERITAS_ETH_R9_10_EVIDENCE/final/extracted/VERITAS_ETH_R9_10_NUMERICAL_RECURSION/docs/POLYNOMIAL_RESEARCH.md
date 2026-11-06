# v0.6.0 — Exact polynomial-semiring tensor laboratory

For Boolean formula F with m clauses and n **declared** variables, define the violation generating polynomial:

\[
H_F(T) = \sum_{x\in\{0,1\}^n} T^{v_F(x)},\qquad
v_F(x)=\#\{\text{clauses falsified by }x\}.
\]

Then the coefficient `[T^j] H_F` counts the assignments violating exactly `j` clauses, the constant term equals `#SAT(F)`, and `H_F(1)=2^n`. The first nonzero coefficient gives the minimum number of clauses violated, hence Max-SAT optimum `m - min_violated`. This also works for repeated literals, tautologies, unused variables, and empty clauses.

`veritas.research.violation_polynomial` performs **generic** bucket elimination over a tensor network whose clause factors take polynomial values `1` for satisfied clauses and `T` for falsified clauses. Equality factors ensure copies of a variable agree. Each entry is an integer polynomial, and multiplication uses exact convolution. The method is exponential in induced width, with limits on edge count, clause count, intermediate tables and runtime.

For `precision_bits=p`, all arithmetic occurs in the coefficient ring `Z/(2^p)`; a term may be omitted only when its product is divisible by `2^p`. This is mathematically exact modular truncation, **not** floating-point pruning. Each returned coefficient is a residue. When `p>n`, coefficients are each at most `2^n`, so the nonnegative residues recover all exact counts; when `p<=n`, do not claim the residues reveal the Max-SAT optimum or exact #SAT.

The polynomial is a simple violation-generating deformation, **not** the OpenAI manuscript's Cauchy wire-identification deformation. The implementation does not reproduce the paper's mode valuations, Hermite tapering, or recursive subexponential complexity theorem. There is no empirical claim of a speed improvement over an industrial #SAT solver.

Reproducibility: `python scripts/validate_v06.py` compares its exact coefficients against independent Boolean enumeration, then checks every modular coefficient against the integer polynomial modulo `2^p`. The local API is `/v1/research/violation-spectrum`.

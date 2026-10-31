# Research roadmap

## v0.3.0 implementation status

The code now contains an end-to-end implementation of the manuscript's
deterministic #k-SAT pipeline:

- Exact disjoint sparsification with deterministic branch selection and a
  depth-first leaf iterator.
- Count-preserving conversion of wide clauses to 3-CNF and an implication
  cycle for bounded-occurrence copies.
- Sparse multilinear F2 polynomials for clause violations and generic systems.
- Shortened Tanner-code parity checks, including deterministic exhaustive
  searches for biased shifts and local codes.
- Greedy selection of additional parity equations by exact common-zero counts.
- High-incidence branching, the integer parity-indicator decomposition, exact
  bivariate truncation, rational Taylor jets, Hermite reconstruction, and the
  shared-measurement summation routine.
- A CLI `subexponential` engine that composes the full reduction chain and
  explicit default work guards for its largest searches.

The implementation streams sparsification leaves, incidence branches, Taylor
substitution pairs, local-code words, and measurement signatures. It does not
retain an exponential list of branch results.

## Remaining work and evidence limits

1. **Independent mathematical audit.** Review each source implementation
   against the exact manuscript version, especially integer lifts, parity
   reductions, and all parameter inequalities. Unit tests are not a proof of
   the theorem.
2. **Large-instance complexity evidence.** The current verification suite
   exercises small exact cases. It does not show that the code reaches the
   asymptotic regime, meets the claimed bit-operation bounds, or stays within
   polynomial memory on large inputs.
3. **Construction-search practicality.** The deterministic biased-shift,
   local-code, and parity-row searches are implemented by direct enumeration,
   as in the existence/derandomization arguments. Their actual constants can
   make them unusable. Better search engineering may improve wall time while
   preserving deterministic guarantees.
4. **Arithmetic and resource instrumentation.** Add evidence reports for
   rational numerator/denominator bit lengths, intermediate matrix sizes,
   candidate counts, peak resident memory, and per-stage time. Compare these
   against the manuscript's bounds before making performance claims.
5. **Independent qualification.** No external proof review, large-scale
   resource qualification, or independent reproduction has been completed.
   Keep those statuses distinct from local test results.

## Verification gates

- Differentially compare each count-preserving transformation with exhaustive
  enumeration on small formulas, including empty clauses, isolated variables,
  repeated literals, tautologies, and overlapping sparsification petals.
- Verify each initial Tanner matrix's row count, row length, and minimum
  distance property directly on bounded toy parameters.
- Check that every selected parity-row minimization is exact and that the final
  common-zero set equals the formula's satisfying assignments.
- Verify exact design inequalities and row-space/restoration identities for
  every common-zero counter branch.
- Test a clean extracted source archive and Windows command script.
- Keep correctness evidence, asymptotic proof review, runtime measurements,
  and independent qualification separate in all release notes.

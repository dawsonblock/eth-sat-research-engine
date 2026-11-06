# VERITAS-ETH v2.5: mathematical scope, proof obligations and implementation contract

## Provenance

Built cumulatively from the local v2.4.0 full ZIP. Target reference: OpenAI's
October 25, 2026 manuscript, source file `build/main_full_version.tex`,
https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/main_full_version.tex

The source and accompanying Lean code were *not* vendored or re-proven here.

## Implemented in v2.5

1. `MANUSCRIPT_EXACT`: integer-only evaluation of the parameter formulas
   `lambda=ceil(log2(s))`, `r=64`, `eps=1/131072`,
   `u_d=floor(lambda/(131072*2**d))`,
   `a_d=2*sum(u_j,j=0..d)`, `L=2**a_d`.
   Eligibility here means **only** the `u_d>0` threshold; no other theorem
   premise is thereby certified. No enormous packet is allocated.
2. `EXPERIMENTAL_SCALED`: `2<=r<=64`, `1<=a<=5`. Explicitly not covered by
   the ETH theorem.
3. Exact conditional-expectation symbol assignment minimizing *endpoint-side
   squared load deviations*. This is a different objective from the original
   proof's pair-collision potential. No D.3 derandomization claim.
4. Packet embedding into `2**a` slots: each packet fixes an unordered symbol
   pair at each coordinate, orientation selected by slot bits. Slots are
   padded with inert nulls. Construction does not modify or duplicate wires.
5. Separate independent checker validates label ranges, every real wire
   exactly once, per-coordinate slot alignment, padded slots, packet count
   `packet_count*L<=3*M`, and side/symbol load `max_load*r<=3*M`.
   Bounds may fail on finite scaled experiments, in which case the checker
   explicitly returns `STRUCTURE_ONLY_BOUNDS_NOT_MET`.
6. Exact finite 2-adic extension ring `(Z/2**p Z)[U]/(f(U))`, with a
   deterministic Rabin GF(2) irreducibility test, unit inversion by Newton
   lifting and zero/nonunit rejection. Jet ring `R[V]/(V**ell)`, exact
   truncated multiplication and inversion.
7. Exact, bounded Cauchy kernel polynomials `W_xy(T)`; checks `W(0)=I`
   and vanishing at all nonmatching integer nodes.
8. Pydantic-validated research endpoints, a standalone CLI,
   randomized tests and explicit status reporting.

## Nonclaims and blockers

- This is NOT the complete D.3 manuscript proof or its deterministic
  global collision-potential minimizer. Passing a finite checker is not a
  theorem that such certificates always exist for eligible networks.
- The full D.4.3 deformation across all recursive tensors has NOT been
  integrated with the new packet constructor. The local Cauchy polynomial
  identity is checked only in bounded exact reference mode.
- A complete paper-specific coefficient ring with all recursive canonical
  lift and interpolation-point schedules is not implemented.
- There is NO manuscript D.4.4 weighted-mode counting theorem, specialized
  child-tensor recurrence, or subexponential runtime implementation.
- There is NO proof-to-code correspondence certification or production
  performance claim. Inherited generic SAT/#SAT algorithms may have
  exponential worst-case complexity.

## Formal acceptance gates

* M0: preserve v2.4, tests, and source/documentation traceability. COMPLETE.
* M1a: exact parameters and finite independently checked packets. COMPLETE.
* M1b: full manuscript deterministic D.3 construction and guarantee. OPEN.
* M2a: exact base extension ring and truncated jets for small cases. COMPLETE.
* M2b: complete typed canonical lifts, recursive extension-ring interpolation,
  precision propagation and proofs. OPEN.
* M3a: local Cauchy polynomial identity tests. COMPLETE.
* M3b: full packet-deformed tensor product over the manuscript ring. OPEN.
* M4+: tapered Hermite reconstruction, weighted modes, specialized recursion,
  complete asymptotic proof audit. OPEN.

## Threat model and verification

Checker reads untrusted certificates, recomputes all values, and ignores
self-reported scores. Never classify as PROOF_CHECKED_ for the paper theorem.
Malformed or over-budget packet input fails closed. `--enforce-bounds`
rejects a finite structural arrangement that fails the numeric bounds.

Reference code does not implement constant-time arithmetic and should not
be used for secret key material or confidential cryptographic operations.

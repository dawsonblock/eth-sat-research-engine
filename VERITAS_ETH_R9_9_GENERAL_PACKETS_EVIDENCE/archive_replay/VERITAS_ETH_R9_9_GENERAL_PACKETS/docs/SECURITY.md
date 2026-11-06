# Threat model and operational boundaries

1. **Natural-language distortion.** This build accepts formal symbols only; never interpret the parser output as a reliable translation of ordinary prose. Review primary-variable mappings and assumptions.
2. **Counterexample integrity.** Directly check candidate models under the original CNF or the original propositional AST.
3. **False proof claims.** A DPLL `UNSAT` result is tagged `SOLVER_ONLY`; an UNSAT core is not a complete formal proof. This package does not implement LRAT/DRAT verification.
4. **Resource abuse.** API imposes maximum variable/size/node/time caps. These are best-effort bounds in the same Python process and do not ensure protection against hostile users. Use firewall, authentication, container CPU/RAM/pid limits, and OS-enforced process isolation for multi-user deployment.
5. **Ganak binaries.** Optional executable is trusted local configuration; no command shell is used. Never accept a binary path from an unauthenticated HTTP request. Binary output is parsed strictly and missing counts fail closed.
6. **Audit rewriting.** SQLite hash chaining detects many accidental/tactical edits. Host administrators can rewrite all entries and recompute hashes. Audit timestamps are metadata, not signed. Externally timestamp/sign archive roots for stronger claims.
7. **Data retention.** Submission hashes and returned results are persisted. Hashes of small logical inputs may be susceptible to dictionary attacks. Store the database in a protected local directory.
8. **Privacy.** Browser HTML makes same-origin API requests. No analytics or embedded third-party scripts. API documentation is public to locally reachable clients; do not publicly bind without authentication.
9. **Missing features.** No RBAC, user auth, encryption-at-rest, SIEM connector, attestation, distributed cancellation, strong network isolation, arbitrary code evaluator, or certificate verifier. Do not market this prototype as secure production multi-tenancy.


## v0.5 certificate and counting controls

- UNSAT tree generation is restricted to at most 28 variables, 100,000 generator nodes, and 4 MB serialized certificates. Typical API defaults are tighter. A timeout or size limit returns UNKNOWN or leaves the original result SOLVER_ONLY; incomplete trees are never accepted.
- An independent checker validates every forced literal, binary split, and falsified-clause leaf against the exact CNF SHA-256. It limits serialized size and checked node count. It is not a separately audited executable, and this does not imply globally trusted cryptographic proof-carrying computation.
- Projected counting uses at most 12 projected variables and bounds aggregate DPLL nodes/time. Truncation returns UNKNOWN with count null, never a partial count presented as exact.
- The web API is still **not Internet-exposable**. The default worker runs solver loops in-process; request timeouts are best-effort, not process hard limits. Protect behind a local host and do not submit adversarial unrestricted inputs.

## v0.6 research and counting certificate limits

The counting-certificate generator and checker enforce caps on variables, nodes, byte size and (for generation) time. A completed certificate is an exact logical argument only for the pinned CNF, and does not attest to host integrity. The polynomial research endpoint limits clauses, wire occurrences, dense intermediate table size and elapsed wall-clock time; it runs inside the API process without a separately enforceable memory limit. `precision_bits` values at or below the number of variables provide residues only. Do not expose this service remotely or accept adversarial workloads without separately isolated processes, OS quotas and authentication.

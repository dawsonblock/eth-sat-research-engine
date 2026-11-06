# R9.1 release report alias

The authoritative, freshly updated R9.1 report is
[`RELEASE_REPORT_R91.md`](RELEASE_REPORT_R91.md). This compatibility file is
kept so older references do not point to stale metrics.

Current qualification is a partial research release: Python tests, the Lean
formal-model gate, finite C++ differential checks, and the local packet-slot
address theorem pass. Python/C++ executable refinement, full-run correspondence,
the global edge-to-packet bijection, recursive contraction/recovery, and the
complete complexity proof remain unproved or unimplemented. The theorem path
remains disabled.

The baseline ZIP expected by the R9.1 prompt was unavailable. The available
archive identity and all current commands, counts, tool versions, benchmark
measurements, evidence paths, and qualification flags are recorded in the
authoritative report and `validation/r9_1_baseline.json`.

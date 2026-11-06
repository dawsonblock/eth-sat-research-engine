# SUPERSEDED — do not cite these numbers for the current tree

This bundle records a snapshot of the working tree taken on 2026-11-01, when
it reported 710 tests, 456 manifested files, and an eight-wire tapered-v4 run
that completed under `max_work=2_000_000`.

The tree has since moved on (the current snapshot has 911 tests and 506
manifested files), and **the eight-wire run no longer completes at 2M work
units**: it charges about 2,132,619 units and now fails closed with
`INCONCLUSIVE_RESOURCE_LIMIT` at that cap. `scripts/validate_tapered_v4.py`
therefore pins `max_work=3_000_000`, and both `--write` and `--replay`
succeed at that cap.

What in this directory is still valid:

- The *shape* of the result: the eight-wire forced-assignment CNF has count
  one, the transcript replays, and the largest child has 6 edges for an
  8-edge parent (a 3/4 ratio, so the one-eighth invariant fails — that is a
  genuine property of the finite example, not a stale artifact).
- `eight_wire_child_size_certificate.json` and the `audit_v4_child_sizes.py`
  replay, which still reproduce.

What must be regenerated before citation:

- Any test count, manifested-file count, or work-unit ledger.
- The eight-wire certificate and its replay log, which must be regenerated
  with the current script (the recorded policy carries `max_work=2000000`).

See `VERITAS_ETH_v3.8.2/docs/OPENAI_PAPER_CONFORMANCE.md` §6 and
`VERITAS_ETH_v3.8.2/docs/FINITE_TAPERED_RECURSION_V39.md` for the current
statements.

# Two-level streaming CLI connection

The streaming CLI now accepts `--layout-file`. It checks the original parent
binding before preparing the scalar extension field, then reconstructs and
audits the layout against the new parent digest. Descendants use the same
first-fit singleton strategy checked by the structural preflight.

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r99.stream_cli \
  examples/r99_nonconstant_matching242.json \
  --layout-file examples/r99_nonconstant_matching242_layout.json \
  --levels 2 --preflight-only --max-certificate-bytes 100000000 \
  --output-dir ../two_level_preflight
```

This checks projected 242 -> 22 -> 2 topology without tensor arithmetic.
Omit `--preflight-only` to enter the cached full-tapered executor under explicit
work, call, time, point and evidence limits. Topology admission is not a runtime
feasibility certificate. Legacy recomputing-call and retained-grid estimates
are recorded as advisories; other structural and precision refusals remain.
Preflight work is charged to the execution budget. A small work-budget probe
reaches the Hermite admission check and returns inconclusive with no result.
The complete two-level numerical validation and source qualification remain open.

The adapted report retains the original preflight digest as provenance and
computes a new digest over all adapted fields. A topology-only success supplies
neither a contraction value nor an event stream. The underlying preflight status
is retained; `streaming_topology_admitted` explicitly records the narrower verdict.

The 242-edge fixture is a matching, not a general connected-network acceptance
case. Its 727-point root grid fits the prepared degree-ten residue field. This
solves field capacity and layout wiring, not the cost of computing every point.
The checked one-active-level execution through `--layout-file` is the 22-edge
nonconstant matching, with all 134 points and independent recursive replay.

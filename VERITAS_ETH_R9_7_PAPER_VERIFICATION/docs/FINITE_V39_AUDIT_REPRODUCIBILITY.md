# Finite audit and reproducibility

Run from this directory with the project dependencies installed:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m pytest -q -o addopts=''
PYTHONPATH=src python scripts/validate_v39_child_audit.py
PYTHONPATH=src python scripts/validate_v39_two_level_audit.py --include-four-wire
PYTHONPATH=src python scripts/validate_v39_dense_audit.py --wires 8
PYTHONPATH=src python scripts/validate_v39_dense_audit.py --wires 10
PYTHONPATH=src python scripts/validate_v39_dense_audit.py --wires 12
PYTHONPATH=src python scripts/validate_v39_dense_audit.py --wires 14 --max-reconstruction-ops 160000000
PYTHONPATH=src python scripts/validate_v39_dense_audit.py --wires 16 --max-reconstruction-ops 800000000 --max-live-jet-entries 2500000
python scripts/verify_manifest.py
```

Each dense audit should run in a fresh process for the process peak-RSS value
to be separately meaningful. The generated input tables are deterministic;
their SHA-256 digests, resource caps, partial work counts, and outcomes are
included in each JSON output. RSS, elapsed time, and timeout outcomes depend
on the host. The table and work caps are not hard operating-system memory or
CPU limits.

On the development snapshot tested here, the scalar dense experiment gave
the following results. Its `M+1`-bit Hermite reconstruction recovers the
full Boolean-table dot product when it completes; `reference` is the
independently computed exact dot product. The point evaluation is modulo four.

| Wires | Reference | Independent point identity | Full count reconstruction |
|---:|---:|---|---|
| 8 | 59 | matched | 59 |
| 10 | 274 | matched | 274 |
| 12 | 994 | matched | 994 |
| 14 | 4035 | matched | 4035 with the listed 160-million-operation cap |
| 16 | 16390 | matched | 16390 with the listed operation and live-entry caps |

Before per-node jet truncation, a 14-wire attempt with a 600-million-operation
cap was stopped after a 60-second process timeout, and a 16-wire preflight
estimated 2,677,014,528 scalar operations. Those attempts yielded no count.
After the change, the completed 14- and 16-wire reconstructions counted
141,246,464 and 762,052,608 scalar operations, respectively. The 16-wire
run used 46-bit working precision, estimated 2,228,224 live jet entries,
and observed a process peak RSS of about 119 MB on the test host. These
are finite scalar-reference measurements, not complete bit-cost accounting.

The counted weighted-mode work was 69,138; 416,790; 2,342,938; 12,533,790;
and 64,618,530 scalar operations at 8 through 16 wires, respectively. The
corresponding direct dot-product baselines were 512; 2,048; 8,192; 32,768;
and 131,072. Those counters omit setup and bit complexity. Every retained
scalar term kept full `M`-wire tensor scope. This experiment therefore shows
no work or child-size reduction.

The separate four-wire XOR point-child audit has two modes and four retained
tuples. The checked children each have four wires. Its local mode identity
matches the independent half-edge contraction, but the strict one-eighth
check rejects the branch without returning a count. This is a finite scaled
example, not a counterexample to the theorem's 64-group hypotheses.
A separate two-wire CNF completed two recursion levels and matched its
independent count of three, but its largest observed child had four wires.
A four-wire two-level attempt exhausted its observed work-unit budget (the
run fails closed on charged work, not on the wall clock: it stops at the
`max_work` cap after roughly 14 seconds, well inside the 25-second
cooperative deadline) and returned no count.

An independent rational-polynomial reference exhaustively checks `W(0)=I`,
the geometric-mode expansion, and coefficient divisibility for packet sizes
two and four, subject to its explicit precision and order limits. These are
finite symbolic checks rather than a Lean proof or a general theorem.

The source commit, local patch including new files, interpreter and dependency
versions, test logs, exact commands, and complete JSON outputs are captured in
the companion evidence directory created with this audit. They identify the
local snapshot; they do not establish independent mathematical review,
theorem-scale execution, complete work accounting, or polynomial space.

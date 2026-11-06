# Local validation, v3.8.1 candidate

On the source tree before release packaging, Python 3.12.0 and Python 3.10.19
each completed the full test collection: **518 passed**. The 3.10 environment
used NetworkX 3.4.2. Pytest plugin autoload was disabled, and audit databases
were outside the source tree. The v3.8 and v3.7 40-case validation scripts each
passed on Python 3.12. The archived v3.7 certificate fixture was generated from
the supplied unmodified v3.8.0 source and replayed against this candidate.

`v381_dense_cauchy.json` contains deterministic 8/16-wire scalar experiment
outputs; its SHA-256 is
`0f9c7a59eb80b40a8e4d6dfc667fe9d4bb4888e3cf6a9d4bb7b701a6f9b9c4714da1257`.
It was regenerated and byte-compared. The 8-wire half-edge oracle completed;
the 16-wire direct half-edge oracle remains blocked by its explicit pair cap.
See `docs/CORRECTIONS_V381.md` for limitations of these measurements.

This is local engineering evidence, not a hosted-CI result, independent
security audit, theorem verification, release authorization, or production
qualification. Archive identity must be checked separately after packaging.

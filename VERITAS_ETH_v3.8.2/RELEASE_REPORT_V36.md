# VERITAS-ETH v3.6.0 Release Report

## Scope

Cumulative source upgrade from v3.5.0. Implements an exact finite packet-level Boolean-multilinear coefficient tensor over `(Z/2^p Z)[U]/(f(U))[V]/(V^ell)` using sparse idempotent polynomial multiplication. Uses the independently checked D.3 packing and v3.1 geometric-mode certificate as inputs. Checks coefficients with a separate Boolean Möbius inversion implementation. Contracts the resulting packet tensors with original vertex factors, and compares against the original direct Cauchy half-edge oracle. Includes API, CLI, browser UI, test suite, documentation, and source-linked release hash manifest.

## Verification

- 481 pytest cases collected in the combined test inventory.
- Earlier-version and manuscript tests passed in a separate full batch (pytest exit code 0).
- Later-version tests including v3.6 passed in a second separate full batch (pytest exit code 0).
- A single monolithic test run reached >74% of its collected suite before exceeding the execution time limit; no failure was reported up to that point. The separate passing batches are the release's actual regression evidence.
- New v3.6 tests: 11 passed, including API, resource-limit, adversarial certificate and randomized identities.
- Seeded validation: 40 complete packet-oracle certificates, 40 forged-claim rejections, 577 independently checked Boolean coefficient assignments.
- CLI `construct` and `check` passed for a four-wire example, and 23 targeted v3.5–v3.6 tests passed.

## Remaining research gaps

Not an implementation of the manuscript's special D.4.4 group-local packet tensor coefficient extractor used to form shrinking recursive children. The bound `M_child <= M/8` is not established, and the runtime remains exponential in the worst case. This project does not prove or experimentally establish a subexponential SAT/#SAT algorithm.

## Reproduce

1. Install: `python -m pip install -e .[test]`.
2. New tests: `pytest -q tests/test_v36_packet_tensors.py`.
3. Seeded validation: `python scripts/validate_v36.py`.
4. Packet construction: `veritas-eth36 construct --n 3 --clauses-json "[[1,2],[-2,3]]" --output packet.json`.
5. Check: `veritas-eth36 check --certificate packet.json`.
6. Verify manifest: `python scripts/verify_manifest.py`.

## Source references

OpenAI math repository, October 25 paper, `quantitative-reduction.tex` and `quantitative-contraction.tex`. This finite implementation should not be represented as reproducing the full specialized theorem.

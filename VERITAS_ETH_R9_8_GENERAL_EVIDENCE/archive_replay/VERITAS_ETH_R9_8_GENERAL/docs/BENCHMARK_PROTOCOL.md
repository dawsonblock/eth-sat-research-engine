## v1.9 packet-search benchmark separation

The v1.9 planner-only benchmark records packet score, provable lower bounds,
selected plan and planner latency. Scores are not SAT runtime measurements.
Compare total planner + Cauchy/solver execution separately with the same
relabeled network and exact arithmetic before claiming computational gains.

---

# Benchmark protocol

Run `PYTHONPATH=src python benchmarks/run.py > benchmarks/results.jsonl` on the hardware used for all candidates. For definitive comparisons, freeze CPU model, operating system, Python package versions, Ganak version, git SHA, thermal/power state, timeout/node caps, input seeds, and actual solver arguments. Run the same instance corpus against each algorithm, include failures/timeouts, and compare counts to independent exhaustive enumeration where feasible. Publish input generators and scripts. Never present the baseline's wall-clock times as ETH-specific runtime evidence; the research algorithms have not been coded.

The included benchmark is a smoke suite, not a statistically significant or industry-standard competition. See `scripts/validate_10000.py` for a large deterministic correctness differential suite (small n).


## v1.0 reference baseline

`PYTHONPATH=src python benchmarks/v10_separator.py` compares exact edge enumeration, generic bucket elimination and conventional separator recursion on three tiny instances. The recursive algorithm is not the paper's claimed contraction procedure, and no asymptotic or production speed advantage should be inferred.

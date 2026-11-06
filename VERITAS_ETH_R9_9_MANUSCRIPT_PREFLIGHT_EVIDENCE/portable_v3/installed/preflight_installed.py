from pathlib import Path
from dataclasses import replace
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99 import compare_group_counts, ExecutionSpec, conformance_ledger
from veritas.research.parent_child_r99.preflight import two_level_call_floor
from veritas.research.tapered_v4.provenance import source_binding
parent = load_input(Path(__file__).with_name("groups_cycle484.json"))
policy = replace(DEFAULT_SHRINKING_POLICY,max_calls=2000000)
r = compare_group_counts(parent, policy=policy)
c = {x["groups"]:x for x in r["candidates"]}
assert c[512]["largest_edges_by_depth"] == {"0":484,"1":4}
assert c[512]["recursive_calls_lower_bound"] == 1487873
assert c[512]["root_nonzero_point_tuple_count"] > policy.max_tuples
assert c[64]["recursive_calls_lower_bound"] == 1088564353
assert two_level_call_floor()["minimum_calls"] == 12199681
assert not conformance_ledger()["source_qualified"]
print("PASS_INSTALLED_PREFLIGHT", source_binding()["digest"], ExecutionSpec().content_digest)

"""Independent future topology checks and actual generated-child replay."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from veritas.research.parent_child_r98.group_preflight import preflight_group_recursion, topology_of
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, Refusal
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY, build_zero_node_modes
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r98.constructor import construct_children


ROOT = Path(__file__).resolve().parents[1]


def cycle():
    return load_input(ROOT / "examples/r98_shrinking_cycle484.json")


@pytest.mark.parametrize("groups,calls,depth,precision,largest", ((64,5761,2,34304,44), (512,1025,1,31488,4)))
def test_complete_structural_descendants_have_exact_constant_call_counts(groups,calls,depth,precision,largest):
    parent = cycle()
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    plan = preflight_group_recursion(parent, groups=groups, budget=budget)
    report = plan.report()
    assert plan.required_calls == calls
    assert plan.maximal_depth == depth
    assert plan.maximal_precision == precision
    root = next(e for e in plan.expectations if e.parent_topology == plan.root_topology)
    assert max(root.child_edges) == largest
    assert sum(root.child_edges) == 968
    assert root.crossing_packets == (22 if groups == 64 else 242)
    assert root.nonzero_point_tuples == 1
    assert report["tensor_values_checked"] is False
    assert budget.calls == 0


@pytest.mark.parametrize("groups,bad_edges", ((128,20), (256,8)))
def test_first_transition_shrinks_but_descendants_cannot_reach_leaves(groups,bad_edges):
    with pytest.raises(Refusal, match="zero per-side") as caught:
        preflight_group_recursion(cycle(),groups=groups,budget=Budget(DEFAULT_SHRINKING_POLICY))
    assert caught.value.status == "INCONCLUSIVE_DESCENDANT_PACKING"
    assert caught.value.report["failing_edges"] == bad_edges
    assert caught.value.report["failing_depth"] == 1


def test_1024_groups_refuse_degree_two_root():
    with pytest.raises(Refusal, match="whole vertex") as caught:
        preflight_group_recursion(cycle(),groups=1024,budget=Budget(DEFAULT_SHRINKING_POLICY))
    assert caught.value.report["failing_depth"] == 0


@pytest.mark.parametrize("groups,modes", ((64,22), (512,242)))
def test_general_complete_tuple_domain_refused_before_any_production_call(groups,modes):
    from math import comb
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    with pytest.raises(Refusal, match="weighted tuple") as caught:
        preflight_group_recursion(cycle(),groups=groups,budget=budget,general=True)
    assert caught.value.status == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert caught.value.report["crossing_packets"] == modes
    assert caught.value.report["nonzero_point_tuples"] == comb(31488+modes-1,modes)
    assert budget.calls == 0


@pytest.mark.parametrize("field,value,reason", (("max_precision",32000,"precision"),
                                               ("max_depth",1,"depth"),
                                               ("max_calls",5760,"calls"),
                                               ("max_work",1,"budget"),
                                               ("max_certificate_bytes",1,"evidence")))
def test_preflight_resource_caps_fail_closed(field,value,reason):
    policy=replace(DEFAULT_SHRINKING_POLICY,**{field:value})
    with pytest.raises(Refusal,match=reason):
        preflight_group_recursion(cycle(),budget=Budget(policy))


def test_general_mode_free_matching_predicts_all_complete_grid_invocations():
    parent=load_input(ROOT / "examples/r98_general_matching22.json")
    plan=preflight_group_recursion(parent,budget=Budget(DEFAULT_SHRINKING_POLICY),general=True)
    assert plan.required_calls==8577
    assert plan.maximal_precision==1536
    assert plan.expectations[0].crossing_packets==0
    assert plan.expectations[0].point_terms==134


@pytest.mark.parametrize("groups", (64,512))
def test_projection_matches_every_constructed_child_order_and_incidence(groups):
    parent=cycle()
    budget=Budget(DEFAULT_SHRINKING_POLICY)
    plan=preflight_group_recursion(parent,groups=groups,budget=budget)
    layout=construct_vertex_shrinking_layout(parent,groups=groups,budget=budget)
    modes=build_zero_node_modes(parent,layout,-1,budget=budget)
    children=construct_children(parent,layout,modes,ExponentTuple(modes.content_digest,()),
                                budget=budget,_admitted=True,require_shrink=True)
    assert plan.verify_children(parent,children,budget=budget)["all_actual_child_topologies_match"]
    if groups==64:
        child=next(c for c in children if c.edge_count>4).as_parent(parent)
        layout2=construct_vertex_shrinking_layout(child,groups=groups,budget=budget)
        modes2=build_zero_node_modes(child,layout2,1,budget=budget)
        grandchildren=construct_children(child,layout2,modes2,ExponentTuple(modes2.content_digest,()),
                                         budget=budget,_admitted=True,require_shrink=True)
        assert plan.verify_children(child,grandchildren,budget=budget)["descendants_structurally_packable"]


def test_topology_replay_rejects_same_size_changed_port_order_and_missing_child():
    parent=cycle(); budget=Budget(DEFAULT_SHRINKING_POLICY)
    plan=preflight_group_recursion(parent,groups=512,budget=budget)
    layout=construct_vertex_shrinking_layout(parent,groups=512,budget=budget)
    modes=build_zero_node_modes(parent,layout,1,budget=budget)
    children=construct_children(parent,layout,modes,ExponentTuple(modes.content_digest,()),
                                budget=budget,_admitted=True,require_shrink=True)
    with pytest.raises(ValueError,match="inventory"):
        plan.verify_children(parent,children[:-1],budget=budget)
    with pytest.raises(ValueError,match="root differs"):
        plan.verify_children(replace(parent,ancestry_digest="0"*64),children,budget=budget)
    child=children[0]
    original=child.vertices[0]
    changed=replace(original,ports=tuple(reversed(original.ports)))
    forged=SimpleNamespace(group=0,edge_count=child.edge_count,depth=child.depth,
                           precision=child.precision,vertices=(changed,*child.vertices[1:]))
    with pytest.raises(ValueError,match="projection"):
        plan.verify_children(parent,(forged,*children[1:]),budget=budget)


@pytest.mark.parametrize("groups", (True,63,1025,64.0))
def test_group_options_are_typed_and_bounded_even_for_a_leaf(groups):
    parent=cycle()
    with pytest.raises(ValueError,match="group count"):
        preflight_group_recursion(parent,groups=groups,budget=Budget(DEFAULT_SHRINKING_POLICY))


def test_preflight_is_independent_of_tensor_entries_but_root_binding_is_exact():
    parent=cycle()
    changed=replace(parent,ancestry_digest="0"*64)
    plan=preflight_group_recursion(parent,groups=512,budget=Budget(DEFAULT_SHRINKING_POLICY))
    other=preflight_group_recursion(changed,groups=512,budget=Budget(DEFAULT_SHRINKING_POLICY))
    assert plan.root_topology==other.root_topology
    assert plan.root_digest!=other.root_digest
    assert plan.required_calls==other.required_calls


def test_already_charged_root_does_not_fail_exact_call_budget():
    budget=Budget(replace(DEFAULT_SHRINKING_POLICY,max_calls=1025))
    budget.call(0)
    plan=preflight_group_recursion(cycle(),groups=512,budget=budget,root_call_charged=True)
    assert plan.required_calls==1025

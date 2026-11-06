"""Exercise the corrected contracts outside a checkout, including alternate f."""
from dataclasses import replace
import json
import platform

from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.parent_child_r98 import (
    Budget, ExponentTuple, ModeSet, construct_children, contract_scaled, from_described,
)
from veritas.research.parent_child_r98.model import canonical
from veritas.research.parent_child_r98.modes import build_modes, verify_modes
from veritas.research.parent_child_r98.packing import construct_layout, preconditions
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.tapered_v4.provenance import source_binding

net = TensorNetwork(1, (Factor((0,), (-2,3), "row:0"), Factor((0,), (4,5), "col:0")))
parent = from_described(describe_integer_network(net, creation_precision=5,
                       defining_polynomial=25), root_s=16, precision=5)
budget = Budget()
layout = construct_layout(parent, budget=budget)
modes = build_modes(parent, layout, -1, (0,1,0,0), budget=budget)
assert modes.certificate["irreducible_polynomial"] == 25
beta = ExponentTuple(modes.content_digest, ())
child = construct_children(parent, layout, modes, beta, budget=budget)[0]

def must_reject(fn):
    try:
        fn()
    except ValueError:
        return True
    raise AssertionError("malformed metadata was accepted")

must_reject(lambda: child.as_parent(replace(parent, root_s=17)))
mapping = list(child.edge_map)
first = list(mapping[0]); first[1] = False; mapping[0] = tuple(first)
must_reject(lambda: replace(child, edge_map=tuple(mapping)))
record = modes.certificate
record["jet_length"] = True
forged = ModeSet(layout.content_digest, canonical(record))
must_reject(lambda: verify_modes(parent, layout, forged, budget=Budget()))
result = contract_scaled(parent, levels=1)
assert result["result"] == ((7,0,0,0),)
assert result["mode_basis_scope"] == "ZERO_REDUCED_GEOMETRIC_POINT_MODES"
assert not result["paper_formal_mode_domain_enumerated"]
assert not preconditions(parent)["descendant_schedules_verified"]
assert result["parent_child_recursion_performed"] is True
leaf_result = contract_scaled(parent, levels=0)
assert leaf_result["result"] == result["result"]
assert leaf_result["status"] == "PASS_FINITE_SCALED_LEAF"
assert leaf_result["parent_child_recursion_performed"] is False
print(json.dumps({"status":"PASS_INSTALLED_MATHEMATICAL_CORRECTIONS",
                  "python":platform.python_version(),"defining_polynomial":25,
                  "result":result["result"],"source_binding":source_binding()["digest"],
                  "parent_binding_rejection":True,"boolean_metadata_rejection":True,
                  "leaf_only_status_checked":True,
                  "source_qualified":False}))

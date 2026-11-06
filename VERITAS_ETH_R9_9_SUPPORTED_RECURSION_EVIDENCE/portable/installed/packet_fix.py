import json
import platform
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.parent_child_r98 import Budget, from_described
from veritas.research.parent_child_r98.packing import construct_layout, audit_layout
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.tapered_v4.provenance import source_binding

vertices = []
for i in range(2):
    ports = tuple(range(3*i,3*i+3))
    vertices.extend((Factor(ports,tuple(range(8)),f"row:{i}"),
                     Factor(ports,tuple(range(8)),f"col:{i}")))
parent = from_described(describe_integer_network(TensorNetwork(6,tuple(vertices)),
                       creation_precision=5,defining_polynomial=first_irreducible(5)),
                       root_s=16,precision=5)
layout = construct_layout(parent,budget=Budget())
assert layout.source["H_pad"] == 4
assert any(p["index"] == 1 for p in layout.source["packets"])
report = audit_layout(parent,layout)
assert report["exact_edge_coverage"] and not report["source_eligible"]
print(json.dumps({"status":"PASS_INSTALLED_PACKET_INDEX_CORRECTION",
                  "python":platform.python_version(),"source_binding":source_binding()["digest"],
                  "source_qualified":False}))

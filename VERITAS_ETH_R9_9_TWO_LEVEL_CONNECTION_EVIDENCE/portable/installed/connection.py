from pathlib import Path
from dataclasses import replace
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r99.stream_cli import prepare_layout_input,streaming_preflight
from veritas.research.tapered_v4.provenance import source_binding
here=Path(__file__).parent
policy=replace(DEFAULT_SHRINKING_POLICY,max_certificate_bytes=100000000)
root=load_input(here/'r99_nonconstant_matching242.json')
parent,layout=prepare_layout_input(root,here/'r99_nonconstant_matching242_layout.json',budget=Budget(policy))
assert layout.parent_digest==parent.content_digest!=root.content_digest
report=streaming_preflight(parent,layout,2,4096,policy)
assert report['streaming_topology_admitted'] and not report['source_qualified']
assert source_binding()['digest']=='bfbbd32ccc167a2a17c8525c45e6f77fff879091a2dc71f22cf302999d351c43'
print('PASS_INSTALLED_TWO_LEVEL_CONNECTION')

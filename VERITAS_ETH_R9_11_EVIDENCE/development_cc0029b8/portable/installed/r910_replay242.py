from pathlib import Path
from dataclasses import replace
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.cli import load_execution_report
from veritas.research.parent_child_r910.checker import verify
from veritas.research.parent_child_r910.reference import matching_reference
from veritas.research.tapered_v4.provenance import source_binding
here=Path(__file__).parent
assert source_binding()['digest']=='cc0029b8619f94b7d0173c6cf5e4683836efcb9548a40ec43cdaea29477f0a4a'
p=load_input(here/'r910_matching242.json')
r=load_execution_report(here/'r910_report242.json',max_bytes=100000000)
policy=replace(DEFAULT_SHRINKING_POLICY,max_work=1000000000,max_seconds=600,max_certificate_bytes=100000000)
with (here/'r910_events242.jsonl').open('rb') as stream:
 c=verify(p,(line.rstrip(b'\n') for line in stream),r,policy=policy)
assert c['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY',c
assert c['result']==matching_reference(p)['result']
print('PASS_INSTALLED_R910_242_REPLAY',c['ledger'])

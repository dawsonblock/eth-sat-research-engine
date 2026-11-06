from pathlib import Path
from dataclasses import replace
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.cli import load_execution_report
from veritas.research.parent_child_r910.checker import verify
from veritas.research.tapered_v4.provenance import source_binding
here=Path(__file__).parent
assert source_binding()['digest']=='925b1196f1b5ee1363a97810ef0fca8bbb561a36ffac2c41800a08e236f96702'
p=load_input(here/'r911_cycle_input.json')
r=load_execution_report(here/'r911_cycle_report.json',max_bytes=100000000)
policy=replace(DEFAULT_SHRINKING_POLICY,max_seconds=600,max_certificate_bytes=100000000)
with (here/'r911_cycle_events.jsonl').open('rb') as stream:
 checked=verify(p,(line.rstrip(b'\n') for line in stream),r,policy=policy)
assert checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY',checked
assert checked['source_compatibility']=='CURRENT_SOURCE'
assert checked['result'][0][0]==302982134081445662325614
assert not any(checked['result'][0][1:])
assert r['active_calls_by_depth']=={'0':1}
print('PASS_INSTALLED_R911_CONNECTED_ONE_LEVEL_REPLAY',checked['ledger'])

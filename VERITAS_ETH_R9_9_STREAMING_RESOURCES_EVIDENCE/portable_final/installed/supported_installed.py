from pathlib import Path
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.model import Budget,Policy,canonical
from veritas.research.parent_child_r99.cli import load_layout
from veritas.research.parent_child_r99 import recover_supported_parent,verify_supported_recovery,contract_supported_recursion,verify_recursive_events
base=Path(__file__).parent
p=load_input(base/'r99_multislot_crossing2.json')
policy=Policy(max_work=1000000000,max_seconds=600,max_certificate_bytes=100000000)
l=load_layout(p,base/'r99_multislot_crossing2_layout.json',Budget(policy))
r=recover_supported_parent(p,l,policy=policy)
assert r['status']=='PASS_FINITE_SUPPORTED_PACKET_RECOVERY',r
v=verify_supported_recovery(p,l,r['certificate'],policy=policy)
assert v['status']=='PASS_INDEPENDENT_SUPPORTED_RECOVERY',v
assert r['result']==v['result']==((1,0,0,0),)
print('PASS_INSTALLED_SUPPORTED_CROSSING_RECOVERY',r['ledger']['actual_calls'])

import tempfile
from veritas.research.parent_child_r99.cli import load_execution_report
r=contract_supported_recursion(p)
with tempfile.TemporaryDirectory() as directory:
 path=Path(directory)/'report.json';path.write_bytes(canonical(r))
 loaded=load_execution_report(path,max_bytes=1000000)
 checked=verify_recursive_events(p,[],loaded)
 assert checked['status']=='PASS_INDEPENDENT_SUPPORTED_RECURSION',checked
print('PASS_INSTALLED_EXECUTION_REPORT_REPLAY')

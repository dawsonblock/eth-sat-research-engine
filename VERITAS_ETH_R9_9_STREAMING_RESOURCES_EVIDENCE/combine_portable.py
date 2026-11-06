from pathlib import Path
import json
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE')
old=root/'portable';fresh=root/'portable_final'
a=json.loads((old/'portable_summary_stale_wheel.json').read_text())
b=json.loads((fresh/'portable_summary.json').read_text())
assert b['status']=='PASS'
binding='8c573334553c18e65be712e85e1176e7dc1ffee32a0ba14dbf1693db8410002e'
assert b['implementation_source_sha256']==a['implementation_source_sha256']==binding
assert (root/'docker_final_identity.log').read_text().strip()==binding
wheel=b['commands']; docker=[r for r in a['commands'] if r['name'].startswith('docker_')]
for records,folder in [(wheel,fresh),(docker,old)]:
    for record in records:
        assert record['exit_code']==0 and record['source_before']==record['source_after']==binding
        record['log_path']=str((folder/('portable_'+record['name']+'.log')).relative_to(root))
identity={'name':'docker_source_identity','exit_code':0,'source_before':binding,'source_after':binding,
          'log_path':'docker_final_identity.log','check':'isolated import source_binding equality'}
commands=wheel+docker+[identity]
assert len({r['name'] for r in commands})==len(commands)
b.update(commands=commands,portable_command_count=len(commands),fresh_wheel_evidence_directory='portable_final',
         docker_evidence_directory='portable',stale_installed_wheel_evidence_excluded=True,
         installed_wheel_source_sha256=binding,docker_source_sha256=binding)
(old/'portable_commands_stale_wheel.json').write_bytes((old/'portable_commands.json').read_bytes())
(old/'portable_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
(old/'portable_summary.json').write_text(json.dumps(b,indent=2)+'\n')
print('PASS final portable identity and checks:',len(commands))

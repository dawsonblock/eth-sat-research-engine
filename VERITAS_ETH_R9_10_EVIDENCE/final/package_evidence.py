from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
base=Path(__file__).resolve().parent
workspace=base.parent.parent
full=json.loads((base/'full/summary.json').read_text())
inherited=json.loads((base/'inherited/summary.json').read_text())
portable=json.loads((base/'portable/summary.json').read_text())
assert full['status']==inherited['status']==portable['status']=='PASS'
suites=ET.parse(base/'full/pytest.xml').getroot()
assert all(int(s.attrib.get('failures',0))==int(s.attrib.get('errors',0))==0 for s in suites)
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
counts['passed']=counts['tests']-counts['skipped']
source=full['source']
assert source==inherited['source']==portable['source']
for name in ('numerical/run','numerical242'):
 r=json.loads((base/name/'report.json').read_text());c=json.loads((base/name/'verification.json').read_text())
 assert r['implementation_source_sha256']==source
 assert r['status']=='PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION'
 assert c['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY' and c['result']==r['result']
for name in ('r910_wheel_replay','r910_docker_replay','r910_docker_replay242'):
 assert 'PASS_INSTALLED_R910_' in (base/'portable'/(name+'.log')).read_text()
summary={'status':'PASS_FINITE_NUMERICAL_AND_RELEASE_CHECKS','source_sha256':source,
 'pytest':counts,'inherited_commands':len(inherited['commands']),
 'portable_commands':len(portable['commands']),'additional_installed_replays':3,
 'release_scope':'PARTIAL_FINITE_R910','obligations':json.loads((base/'obligation_status.json').read_text())}
(base/'validation_summary.json').write_text(json.dumps(summary,indent=2))
(base/'EVIDENCE_README.md').write_text('''# R9.10 finite numerical evidence

These certificates require the co-delivered R9.10 source archive. Source qualification and theorem mode remain disabled. The complete resource contract is partial: bit operations are not instrumented, and time/space theorems are unproved.

From the extracted source checkout, independently replay either run with:

    PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli examples/r910_matching235.json --layout-file examples/r910_matching235_layout.json --replay-dir /path/to/evidence/numerical/run --output-dir /new/external/replay235

    PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli examples/r99_nonconstant_matching242.json --layout-file examples/r99_nonconstant_matching242_layout.json --replay-dir /path/to/evidence/numerical242 --output-dir /new/external/replay242

Outputs must be new external directories. `report.json` binds the implementation source and event stream. The checker reconstructs dependencies and numerical contributions; the hashes alone do not prove correctness. `reference.json` records the independent matching-edge integer calculation. The source release report explains the exact zero-tail optimization and remaining obligations.

`validation_summary.json` summarizes the gates. Environment and artifact hashes accompany the results. Times and RSS describe these runs, not universal resource bounds. Historical absolute paths in command logs identify the originating checkout; use the relative reproduction commands above on another machine.
''')
files=[]
for folder in ('numerical','numerical242','baseline22','zero22','bounded242','legacy_bounded242','preflight242','inherited','full'):
 files += [p for p in (base/folder).rglob('*') if p.is_file()]
for name in ('validation_summary.json','environment.json','obligation_status.json','paper-pin.json','numerical_artifact_manifest.json','EVIDENCE_README.md','zero22_input.json','archive.json','git_revision.json','extraction_check.json'):
 p=base/name
 if p.is_file():files.append(p)
for name in ('summary.json','r910_commands.json','r910_wheel_replay.log','r910_docker_replay.log','r910_docker_replay242.log'):
 files.append(base/'portable'/name)
files.append(base/'extracted_replay242/verification.json')
files=sorted(set(files))
manifest={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(base/'EVIDENCE_SHA256.json').write_text(json.dumps(manifest,indent=2,sort_keys=True));files.append(base/'EVIDENCE_SHA256.json')
out=workspace/'VERITAS_ETH_R9_10_NUMERICAL_EVIDENCE.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(files):
  info=zipfile.ZipInfo('R910_EVIDENCE/'+str(p.relative_to(base)),date_time=(2026,11,5,12,0,0));info.external_attr=0o100644<<16
  z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(out) as z:assert z.testzip() is None
result={'path':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(files)}
(base/'evidence_archive.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

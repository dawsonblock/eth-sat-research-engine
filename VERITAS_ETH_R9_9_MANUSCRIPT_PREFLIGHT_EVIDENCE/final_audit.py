import json,hashlib,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT')
base=root.parent/'VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_EVIDENCE'
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
from veritas.research.parent_child_r98.model import decode,canonical,digest
binding=source_binding()['digest']
full=json.loads((base/'full_v2/summary.json').read_text())
inherited=json.loads((base/'inherited_v2/summary.json').read_text())
portable=json.loads((base/'portable_v3/portable_summary.json').read_text())
for obj in (full,inherited,portable):
 assert obj['status']=='PASS',obj['status']
 for c in obj['commands']:
  assert c['exit_code']==0 and c['source_before']==c['source_after']==binding,c['name']
assert len(inherited['commands'])==13 and len(portable['commands'])==26
xml=ET.parse(base/'full_v2/pytest.xml')
suites=xml.findall('.//testsuite')
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts['tests']>=1915 and counts['failures']==counts['errors']==0 and counts['skipped']==2,counts
counts['passed']=counts['tests']-counts['skipped']
skips=[{'name':c.attrib['name'],'class':c.attrib.get('classname'),'reason':c.find('skipped').attrib.get('message')} for c in xml.findall('.//testcase') if c.find('skipped') is not None]
lean=json.loads((base/'inherited_v2/lean.json').read_text())
assert lean['status']=='PASS' and len(lean['results'])==41
assert all(r['axiom_audit']['passed'] for r in lean['results'])
assert not lean['theorem_mode_enabled'] and not lean['universal_python_refinement_proven']
for name in ('groups','matching','point_count'):
 record=decode((base/'final_v2'/f'{name}.json').read_bytes(),cap=100000000)
 hashed=record.pop('report_digest')
 assert hashed==digest(canonical(record)) and record['implementation_source_sha256']==binding
summary={'schema':'VERITAS_R99_PREFLIGHT_RELEASE_VALIDATION_V1','status':'PASS_FINITE_DEVELOPMENT_CHECKS','source_digest':binding,'baseline_commit':'739eb96bd01d1ced559013d0324eadc9b862c4d7','pytest':counts,'skips':skips,'inherited_commands':13,'portable_commands':26,'lean_modules':41,'lean_accepted_axioms':lean['allowed_lean_axioms'],'universal_python_refinement_proven':False,'source_qualified':False,'theorem_mode_enabled':False,'bit_time_bound_status':'COMPLEXITY_NOT_ESTABLISHED','peak_space_bound_status':'COMPLEXITY_NOT_ESTABLISHED','connected_multislot_two_level_full_hermite_acceptance':'NOT_RUN_RESOURCE_GAP','new_constant_row_full_hermite_test':{'points':134,'calls':8577,'point_values_independently_replayed':True,'degree_shortcut_used':False},'full_container_pytest':'NOT_RUN','preliminary_runs':'INTERRUPTED_NOT_RELEASE_EVIDENCE'}
from veritas.research.parent_child_r99.cli import load_execution_report
recursive=load_execution_report(base/'final_v2/recursive_report.json',max_bytes=100000000)
replay=load_execution_report(base/'final_v2/recursive_replay.json',max_bytes=100000000)
closed=json.loads((base/'final_v2/closed_form.json').read_text())
commands=json.loads((base/'final_v2/recursive_commands.json').read_text())
assert len(commands)==3 and all(c['exit_code']==0 and c['source']==binding for c in commands)
assert recursive['status']=='PASS_FINITE_SUPPORTED_SHRINKING_RECURSION'
assert replay['status']=='PASS_INDEPENDENT_SUPPORTED_RECURSION'
assert closed['status']=='PASS_INDEPENDENT_MATCHING242_CAUCHY_FORMULA'
assert recursive['implementation_source_sha256']==binding
assert recursive['result']==replay['result']==[[17*2**241,0]]
assert recursive['largest_edges_by_depth']=={'0':242,'1':22,'2':2}
assert recursive['ledger']['actual_calls']==56449
assert not recursive['source_qualified'] and not recursive['source_tapered_functional_used']
summary['fresh_two_level_regression']={'largest_edges_by_depth':recursive['largest_edges_by_depth'],'actual_calls':56449,'points':recursive['ledger']['point_evaluations'],'precision':recursive['maximum_precision'],'independent_replay':'PASS','eight_root_points_closed_form':'PASS','recovery':'DEGREE_CERTIFIED_TAYLOR_NOT_FULL_TAPERED','events_sha256':hashlib.sha256((base/'final_v2/recursive.events').read_bytes()).hexdigest()}
(base/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
files=[]
for sub in ('full_v2','inherited_v2','final_v2','portable_v3'):
 for f in (base/sub).rglob('*'):
  if f.is_file() and not any(part in ('clean_py310','installed','wheels','__pycache__') for part in f.relative_to(base).parts) and f.suffix in ('.json','.log','.xml','.py'):
   files.append(f)
files.append(base/'validation_summary.json')
(base/'REVIEW_SHA256.json').write_text(json.dumps({str(f.relative_to(base)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)},indent=2)+'\n')
print(json.dumps(summary))

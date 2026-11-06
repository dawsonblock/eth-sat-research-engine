from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
base=Path(__file__).resolve().parent
workspace=base.parent.parent
read=lambda p:json.loads(p.read_text())
full,inherited,portable=(read(base/n/'summary.json') for n in ('full','inherited','portable'))
assert full['status']==inherited['status']==portable['status']=='PASS'
assert len(inherited['commands'])==13 and len(portable['commands'])==35
source=full['source'];assert source==inherited['source']==portable['source']
for record in (full,inherited,portable):
 assert all(c['exit_code']==0 and c['source_before']==c['source_after']==source for c in record['commands'])
suites=ET.parse(base/'full/pytest.xml').getroot()
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts['failures']==counts['errors']==0
counts['passed']=counts['tests']-counts['skipped']
for n in ('235','242'):
 receipt=read(base/('replay'+n)/'verification.json')
 old=read(base/'sealed_r910'/n/'report.json')
 assert receipt['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
 assert receipt['result']==old['result'] and receipt['checker_source_sha256']==source
 assert receipt['producer_source_sha256']==old['implementation_source_sha256']
for name,resource in [('refused_oracle_work','WORK_UNITS'),('refused_oracle_time','WALL_TIME_US')]:
 r=read(base/name/'verification.json');assert r['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'result' not in r
 assert r['resource_failure']['resource']==resource
assert read(base/'numerical/summary.json')['status']=='PASS_FINITE_R910_NUMERICAL_GATES'
experiments=read(base/'experiment_summary.json');assert experiments['source_sha256']==source
obligations=read(base/'obligation_status.json')
obligations['certificate_portability']['status']='PASS_LOCAL_CLEAN_WHEEL_AND_DOCKER'
(base/'obligation_status.json').write_text(json.dumps(obligations,indent=2))
summary={'status':'PASS_PORTABILITY_RELEASE_CHECKS_GENERALIZATION_PARTIAL','source_sha256':source,
 'pytest':counts,'inherited_commands':13,'portable_commands':35,
 'connected_two_active_level_gate':'INCONCLUSIVE_RESOURCE_LIMIT',
 'connected_one_level_reference_and_replay':'PASS_WITH_AND_WITHOUT_CACHE',
 'source_qualified':False,'theorem_mode_enabled':False,'obligations':obligations}
(base/'validation_summary.json').write_text(json.dumps(summary,indent=2))
(base/'EVIDENCE_README.md').write_text('''# R9.11 portability evidence — partial generalization

Use the co-delivered R9.11 source archive. The new checker fully replays the
unchanged sealed R9.10 certificates in `sealed_r910/235` and `sealed_r910/242`.
The reports retain their old producer identity. No theorem mode is enabled.

From the extracted source checkout:

    PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli /path/to/evidence/sealed_r910/235/input.json --layout-file /path/to/evidence/sealed_r910/235/layout.json --replay-dir /path/to/evidence/sealed_r910/235 --output-dir /new/external/replay235 --max-seconds 600 --oracle-max-seconds 600 --oracle-max-work 5000000

Replace `235` with `242` to replay the other certificate. Output directories must
be new and external. The fresh R9.11 235-wire producer stream is in `numerical/run`.
Successful connected one-level streams and separate transfer references are in
`coupled_one_level` and `coupled_one_level_no_cache`.

`coupled_core`, `coupled_core_100mb`, `fully_nonconstant_cycle`, `sweep`, and
`sweep_shifted` contain bounded refusals. They do not contain successful parent
answers. The earlier driver snapshots preserve the original script bytes for
those attempts; each plan records its driver hash. The latest driver is in the
source archive. `experiment_summary.json` describes actual partial progress.

`validation_summary.json` records the completed release checks and open gates.
`portable/commands.json` and its logs include clean-wheel and Docker replays of
both sealed certificates. Rebuild the wheel/image from the supplied source to
repeat them; virtual environments and container images are not archived.
Historical absolute paths identify the originating environment.

Timing measurements are shared-host observations. Charged work is not exact bit
cost; interrupted oracle work can be pending outside the global ledger. Working
space, asymptotic bounds, the manuscript-active schedule, arbitrary jet length,
and executable refinement are not established. Hashes check byte consistency,
not author identity or mathematical validity.
''')
files=[]
for folder in ('numerical','sealed_r910','replay235','replay242','refused_oracle_work','refused_oracle_time',
 'coupled_core','coupled_core_100mb','coupled_one_level','coupled_one_level_no_cache','fully_nonconstant_cycle',
 'sweep','sweep_shifted','inherited','full','extracted_replay235'):
 files += [p for p in (base/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [p for p in base.iterdir() if p.is_file() and p.name not in ('EVIDENCE_SHA256.json','evidence_archive.json','evidence_verification.json')]
files += [p for p in (base/'portable').glob('*') if p.is_file()]
files += [p for p in (base/'portable/installed').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files=sorted(set(files))
manifest={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(base/'EVIDENCE_SHA256.json').write_text(json.dumps(manifest,indent=2,sort_keys=True));files.append(base/'EVIDENCE_SHA256.json')
out=workspace/'VERITAS_ETH_R9_11_PORTABILITY_EVIDENCE.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(files):
  info=zipfile.ZipInfo('R911_EVIDENCE/'+str(p.relative_to(base)),date_time=(2026,11,5,12,0,0));info.external_attr=0o100644<<16
  z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for name,wanted in manifest.items():assert hashlib.sha256(z.read('R911_EVIDENCE/'+name)).hexdigest()==wanted
result={'path':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(files),'manifest_entries_verified':len(manifest)}
(base/'evidence_archive.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

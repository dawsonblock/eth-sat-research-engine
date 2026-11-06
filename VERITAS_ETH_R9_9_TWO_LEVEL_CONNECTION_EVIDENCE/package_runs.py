from pathlib import Path, PurePosixPath
import hashlib,json,subprocess,zipfile
base=Path(__file__).resolve().parent
root=base.parent/'VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION'
evidence=base/'final'
build=base.parent/'VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_FULL_BUILD.zip'
output=base.parent/'VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_RUNS.zip'
sha=lambda data:hashlib.sha256(data).hexdigest()
summary=json.loads((evidence/'validation_summary.json').read_text())
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
for name,expected in json.loads((evidence/'REVIEW_SHA256.json').read_text()).items():
 assert sha((evidence/name).read_bytes())==expected,name
payload={}
for p in sorted(evidence.rglob('*')):
 rel=p.relative_to(evidence)
 if rel.parts[0]=='extracted' or 'clean_py310' in rel.parts or '__pycache__' in rel.parts:continue
 if p.is_symlink():raise RuntimeError(f'Unexpected symlink: {p}')
 if p.is_file():payload['final/'+rel.as_posix()]=p.read_bytes()
for name in ['r99_nonconstant_matching242.json','r99_nonconstant_matching242_layout.json','r98_general_matching22.json']:
 payload['inputs/'+name]=(root/'examples'/name).read_bytes()
payload['inputs/layout22.json']=(base/'layout22.json').read_bytes()
payload['package_runs.py']=Path(__file__).read_bytes()
metadata={'schema':'VERITAS_R99_RUN_ARCHIVE_V1','source_commit':commit,
 'implementation_source_sha256':summary['implementation_source_sha256'],
 'build_archive':build.name,'build_archive_sha256':sha(build.read_bytes()),
 'scope':'Final validated finite connection evidence, including inconclusive resource probe.',
 'excluded':['pre-correction preliminary runs','final/extracted duplicate source tree','portable/clean_py310 regenerated environment','__pycache__'],
 'source_qualified':False,'full_two_active_level_numerical_validation':'NOT_RUN_RESOURCE_GAP'}
payload['ARCHIVE_INFO.json']=(json.dumps(metadata,indent=2)+'\n').encode()
payload['README.md']=b'''# VERITAS-ETH R9.9 validated run evidence

Companion to VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_FULL_BUILD.zip.
ARCHIVE_INFO.json binds the source commit, implementation digest and build ZIP.
SHA256_MANIFEST.json covers every payload file; SHA256SUMS.txt also covers that
manifest. These hashes establish integrity, not a cryptographic signature.

Start with final/validation_summary.json. Raw records are under:
- final/executed22: full 22-edge point execution and independent replay.
- final/topology: projected 242 -> 22 -> 2 topology only; no contraction value.
- final/bounded_run: 242-edge work-budget refusal; no contraction value.
- final/full: full pytest and C++ results.
- final/inherited: inherited numerical and Lean validation.
- final/portable: clean-wheel/Docker logs, checks, fixtures and built wheel.
- inputs: exact root inputs/layouts used for the connected CLI checks.

The source-qualified algorithm and complete two-active-level numerical run
remain unestablished. Preliminary outputs from before the final source
correction are not included. The rejected initial wheel-install summary is
retained in final/portable/initial_install_failure.json; final successful
installation and identity checks are recorded in final/portable/summary.json.

Historical run scripts and logs retain original absolute machine paths.
Adjust those paths before rerunning; this archive is not a captured Python
virtual environment or Docker image. Regenerable virtual environments and the
duplicate extracted build were excluded. The companion build contains source,
tests, proofs, packaging definitions and the documented CLI.
'''
files={name:sha(data) for name,data in sorted(payload.items())}
payload['SHA256_MANIFEST.json']=(json.dumps({'files':files},indent=2)+'\n').encode()
payload['SHA256SUMS.txt']=(''.join(f'{sha(data)}  {name}\n' for name,data in sorted(payload.items()))).encode()
prefix='VERITAS_ETH_R9_9_TWO_LEVEL_CONNECTION_RUNS/'
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,data in sorted(payload.items()):
  info=zipfile.ZipInfo(prefix+name,date_time=(2026,11,5,0,0,0));info.external_attr=0o100644<<16
  z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(set(z.namelist()))==len(payload)
 for name in z.namelist():
  assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
 for name,digest in json.loads(z.read(prefix+'SHA256_MANIFEST.json'))['files'].items():assert sha(z.read(prefix+name))==digest,name
 for line in z.read(prefix+'SHA256SUMS.txt').decode().splitlines():
  digest,name=line.split('  ',1);assert sha(z.read(prefix+name))==digest,name
 result={'archive':str(output),'bytes':output.stat().st_size,'files':len(payload),'sha256':sha(output.read_bytes()),'verification':'PASS_ALL_MEMBER_HASHES_AND_CRC'}
output.with_suffix('.zip.manifest.json').write_text(json.dumps(result,indent=2)+'\n')
(base/'package_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

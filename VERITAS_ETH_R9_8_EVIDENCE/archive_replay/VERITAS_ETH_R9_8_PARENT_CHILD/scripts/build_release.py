"""Build a deterministic, SHA-256-manifested source ZIP next to the source directory.

`python scripts/build_release.py` from anywhere after running tests. Archive
member order, metadata timestamps, modes and compression are deterministic.
Not a cryptographic signature: verify provenance separately.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from hashlib import sha256
import json
import argparse

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output-name', default='VERITAS_ETH_R9_1_CPP_LEAN_REFINEMENT_FULL_UPGRADED.zip',
                    help='ZIP filename written beside the source directory')
args=parser.parse_args()
if Path(args.output_name).name != args.output_name or not args.output_name.endswith('.zip'):
    raise SystemExit('--output-name must be a plain .zip filename')
output=root.parent/args.output_name
ignored={'.git','.veritas','.pytest_cache','__pycache__','.venv','build',
         '.mypy_cache','.ruff_cache','.tox','.eggs','.hypothesis','.nox',
         '.cache','node_modules','dist'}
binary_suffixes={'.pyc','.pyo','.so','.dylib','.dll','.exe','.o','.a','.olean'}
sensitive_names={'.env','.env.local','.env.production','id_rsa','id_ed25519',
                 'credentials.json'}
entries=list(root.rglob('*'))
for path in entries:
    relative=path.relative_to(root)
    if ignored & set(relative.parts):
        continue
    if path.is_symlink():
        raise RuntimeError(f'refusing symlink in release input: {relative.as_posix()}')
    if path.is_file() and (path.name in sensitive_names or path.suffix.lower() in {'.pem','.p12','.pfx'}):
        raise RuntimeError(f'refusing secret-like file in release input: {relative.as_posix()}')
    if path.is_file() and path.suffix.lower() in binary_suffixes:
        raise RuntimeError(f'refusing compiled binary in release input: {relative.as_posix()}')
files=sorted((p for p in entries if p.is_file()
              and not (ignored & set(p.relative_to(root).parts))
              and p.name != '.DS_Store'
              and not any(part.endswith('.egg-info') for part in p.relative_to(root).parts)
              and p.name not in ('SHA256SUMS.txt','SHA256_MANIFEST.json')),
              key=lambda p:p.relative_to(root).as_posix())
json_manifest = {'files': {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
                           for p in files}}
(root/'SHA256_MANIFEST.json').write_text(json.dumps(json_manifest, indent=2)+'\n',encoding='utf-8')
files=sorted(files+[root/'SHA256_MANIFEST.json'], key=lambda p:p.relative_to(root).as_posix())
manifest='\n'.join(f'{sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}'
                   for p in files)+'\n'
(root/'SHA256SUMS.txt').write_text(manifest,encoding='utf-8')
from verify_manifest import verify
verify(root)
with ZipFile(output,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
    for p in files+[root/'SHA256SUMS.txt']:
        name=f'{root.name}/{p.relative_to(root).as_posix()}'
        info=ZipInfo(name,date_time=(2026,10,31,12,0,0))
        info.compress_type=ZIP_DEFLATED
        info.external_attr=0o100644<<16
        z.writestr(info,p.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
with ZipFile(output) as z:
    names=z.namelist()
    if z.testzip() is not None or len(names)!=len(files)+1 or len(set(names))!=len(names):
        raise RuntimeError('release archive verification failed')
    if any(PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
           or '\\' in name for name in names):
        raise RuntimeError('unsafe release archive member path')
    member_hashes = {
        name: sha256(z.read(name)).hexdigest()
        for name in sorted(z.namelist())
    }
archive_sha256 = sha256(output.read_bytes()).hexdigest()
sidecar = output.with_suffix(output.suffix + '.manifest.json')
sidecar.write_text(json.dumps({
    'schema': 'VERITAS_ETH_RELEASE_ZIP_MANIFEST_V1',
    'archive_sha256': archive_sha256,
    'member_count': len(member_hashes),
    'members': member_hashes,
}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({'zip':str(output),'manifest_sidecar':str(sidecar),
    'files':len(files)+1,'manifested':len(files),'bytes':output.stat().st_size,
    'sha256':archive_sha256},indent=2))

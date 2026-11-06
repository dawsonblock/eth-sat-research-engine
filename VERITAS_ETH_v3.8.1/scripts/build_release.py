"""Build a deterministic, SHA-256-manifested source ZIP next to the source directory.

`python scripts/build_release.py` from anywhere after running tests. Archive
member order, metadata timestamps, modes and compression are deterministic.
Not a cryptographic signature: verify provenance separately.
"""
from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from hashlib import sha256
import json

root=Path(__file__).resolve().parents[1]
output=root.parent/(root.name+'_FULL_UPGRADED.zip')
ignored={'.git','.veritas','.pytest_cache','__pycache__','.venv',
         '.mypy_cache','.ruff_cache','.tox','.eggs'}
files=sorted((p for p in root.rglob('*') if p.is_file()
              and not (ignored & set(p.relative_to(root).parts))
              and p.suffix not in ('.pyc','.pyo')
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
    if z.testzip() is not None or len(z.namelist())!=len(files)+1:
        raise RuntimeError('release archive verification failed')
print(json.dumps({'zip':str(output),'files':len(files)+1,
    'manifested':len(files),'bytes':output.stat().st_size,
    'sha256':sha256(output.read_bytes()).hexdigest()},indent=2))

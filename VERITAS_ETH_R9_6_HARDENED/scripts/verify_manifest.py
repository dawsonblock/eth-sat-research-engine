"""Check the co-delivered SHA-256 manifest, including with Python -O.

This verifies consistency only; a manifest distributed alongside the files
is not an authenticated signature or a proof of provenance.
"""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
import sys

# Kept in sync with scripts/build_release.py: every entry here is a cache or a
# build product, never a release input. A tool cache appearing during a test
# run must not be mistaken for an unlisted release file.
IGNORED_DIRS = {'.git', '.veritas', '.pytest_cache', '__pycache__', '.venv',
                '.mypy_cache', '.ruff_cache', '.tox', '.eggs', 'build',
                '.hypothesis', '.nox', '.cache', 'node_modules', 'dist'}


def payload_file(path):
    return (not any(part in IGNORED_DIRS or part.endswith('.egg-info') for part in path.parts)
            and path.suffix not in ('.pyc', '.pyo'))


def verify(root):
    root = root.resolve()
    entries = {}
    for line in (root / 'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
        parts = line.split('  ', 1)
        if len(parts) != 2 or not re.fullmatch(r'[0-9a-f]{64}', parts[0]):
            raise ValueError('invalid manifest line')
        expected, rel = parts
        relative = PurePosixPath(rel)
        if (not rel or relative.is_absolute() or '..' in relative.parts or
                relative.as_posix() != rel or '\\' in rel or rel == 'SHA256SUMS.txt'):
            raise ValueError(f'invalid manifest path: {rel}')
        if rel in entries:
            raise ValueError(f'duplicate manifest path: {rel}')
        path = root.joinpath(*relative.parts)
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'manifest path outside release: {rel}')
        if not path.is_file():
            raise ValueError(f'missing {rel}')
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'checksum mismatch: {rel}')
        entries[rel] = expected
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
              if p.is_file() and payload_file(p.relative_to(root))}
    expected_paths = set(entries) | {'SHA256SUMS.txt'}
    if actual != expected_paths:
        raise ValueError(f'file-set mismatch, extra={sorted(actual-expected_paths)}, '
                         f'missing={sorted(expected_paths-actual)}')
    return len(entries)


if __name__ == '__main__':
    try:
        count = verify(Path(__file__).resolve().parents[1])
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1)
    print(f'PASS: {count} complete file hashes match release manifest; no unlisted files')

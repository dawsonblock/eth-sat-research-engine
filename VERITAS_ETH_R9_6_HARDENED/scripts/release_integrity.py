"""Immutable release-input integrity for the VERITAS-ETH release tree.

Three distinct artefacts, deliberately not merged:

* **release-input manifest** (``SHA256SUMS.txt``) -- the immutable bytes that
  were published with the release: source, proofs, paper sources and the
  historical evidence documents.  It is *read*, never rewritten here.
* **runtime-evidence manifest** -- hashes of files this job just generated.
  It lives outside the release tree and proves only byte identity of fresh
  output; it is not part of the release inputs.
* **integrity snapshot** -- a full path/hash census taken before any step of
  a CI job runs.  Comparing against it afterwards proves that no tracked
  release input changed while the job ran.

A hash proves byte identity.  It is not a publisher signature, a proof of
provenance, or a mathematical certificate.

Usage::

    python scripts/release_integrity.py verify
    python scripts/release_integrity.py snapshot --output S.json
    python scripts/release_integrity.py compare  --snapshot S.json
    python scripts/release_integrity.py evidence --output E.json --directory DIR

Exit codes: 0 = pass, 1 = integrity failure, 2 = usage or I/O failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from hashlib import sha256
from pathlib import Path, PurePosixPath

SCHEMA_SNAPSHOT = "VERITAS_RELEASE_INPUT_SNAPSHOT_V1"
SCHEMA_EVIDENCE = "VERITAS_RUNTIME_EVIDENCE_MANIFEST_V1"

MANIFEST_NAME = "SHA256SUMS.txt"
# Kept in sync with scripts/verify_manifest.py and scripts/build_release.py.
IGNORED_DIRS = {".git", ".veritas", ".pytest_cache", "__pycache__", ".venv",
                ".mypy_cache", ".ruff_cache", ".tox", ".eggs", "build",
                ".hypothesis", ".nox", ".cache", "node_modules", "dist"}
IGNORED_SUFFIXES = (".pyc", ".pyo")


def payload_file(path: Path) -> bool:
    """True when a path participates in the release-input file set."""
    return (not any(part in IGNORED_DIRS or part.endswith(".egg-info")
                    for part in path.parts)
            and path.suffix not in IGNORED_SUFFIXES)


def parse_manifest(root: Path) -> dict[str, str]:
    """Parse and structurally validate the release-input manifest."""
    root = root.resolve()
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        raise ValueError(f"release-input manifest is missing: {MANIFEST_NAME}")
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError("invalid manifest line")
        expected, rel = parts
        if any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("invalid manifest digest")
        relative = PurePosixPath(rel)
        if (not rel or relative.is_absolute() or ".." in relative.parts
                or relative.as_posix() != rel or "\\" in rel
                or rel == MANIFEST_NAME):
            raise ValueError(f"invalid manifest path: {rel}")
        if rel in entries:
            raise ValueError(f"duplicate manifest path: {rel}")
        entries[rel] = expected
    if not entries:
        raise ValueError("release-input manifest is empty")
    return entries


def verify(root: Path, *, expected: dict[str, str] | None = None) -> dict:
    """Verify every manifest entry and the exact release-input file set."""
    root = root.resolve()
    entries = expected if expected is not None else parse_manifest(root)
    mismatched, missing = [], []
    for rel, digest in entries.items():
        path = root.joinpath(*PurePosixPath(rel).parts)
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"manifest path outside release: {rel}")
        if not path.is_file():
            missing.append(rel)
            continue
        if sha256(path.read_bytes()).hexdigest() != digest:
            mismatched.append(rel)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
              if p.is_file() and payload_file(p.relative_to(root))}
    expected_paths = set(entries) | {MANIFEST_NAME}
    return {
        "checked": len(entries),
        "mismatched": sorted(mismatched),
        "missing": sorted(missing),
        "unlisted": sorted(actual - expected_paths),
        "absent": sorted(expected_paths - actual),
        "manifest_sha256": sha256((root / MANIFEST_NAME).read_bytes()).hexdigest(),
    }


def snapshot(root: Path) -> dict:
    """Full census of release-input bytes plus the manifest itself."""
    root = root.resolve()
    entries = parse_manifest(root)
    files = {}
    for rel in sorted(entries):
        path = root.joinpath(*PurePosixPath(rel).parts)
        if path.is_file():
            files[rel] = sha256(path.read_bytes()).hexdigest()
    files[MANIFEST_NAME] = sha256((root / MANIFEST_NAME).read_bytes()).hexdigest()
    return {
        "schema": SCHEMA_SNAPSHOT,
        "trust_class": "HASH_MATCH_UNSIGNED",
        "manifest_entries": len(entries),
        "files": files,
    }


def compare(root: Path, recorded: dict) -> dict:
    """Compare the live tree against a snapshot and a fresh manifest check."""
    root = root.resolve()
    if not isinstance(recorded, dict) or recorded.get("schema") != SCHEMA_SNAPSHOT:
        raise ValueError("unrecognised snapshot schema")
    previous = recorded.get("files")
    if not isinstance(previous, dict) or not previous:
        raise ValueError("snapshot has no file census")
    current = snapshot(root)
    now = current["files"]
    added = sorted(set(now) - set(previous))
    removed = sorted(set(previous) - set(now))
    modified = sorted(rel for rel in set(now) & set(previous)
                      if now[rel] != previous[rel])
    manifest = verify(root)
    stable = not (added or removed or modified) and not (
        manifest["mismatched"] or manifest["missing"] or manifest["unlisted"]
        or manifest["absent"])
    return {
        "schema": "VERITAS_RELEASE_INPUT_COMPARISON_V1",
        "added": added,
        "removed": removed,
        "modified": modified,
        "release_inputs_stable": stable,
        "manifest": manifest,
        "trust_class": "HASH_MATCH_UNSIGNED",
    }


def evidence_manifest(directories, root: Path | None = None) -> dict:
    """Hash freshly generated evidence.  Separate from the release inputs."""
    base = Path(root).resolve() if root is not None else None
    files = {}
    for directory in directories:
        path = Path(directory)
        if not path.is_dir():
            raise ValueError(f"evidence directory is absent: {directory}")
        for member in sorted(path.rglob("*")):
            if member.is_file() and member.suffix not in IGNORED_SUFFIXES:
                rel = (member.relative_to(base).as_posix() if base is not None
                       else member.as_posix())
                if rel in files:
                    raise ValueError(f"duplicate evidence path: {rel}")
                files[rel] = sha256(member.read_bytes()).hexdigest()
    return {
        "schema": SCHEMA_EVIDENCE,
        "role": "RUNTIME_EVIDENCE_NOT_RELEASE_INPUT",
        "files": files,
        "trust_class": "HASH_MATCH_UNSIGNED",
        "note": ("These hashes describe bytes produced by this run. They are "
                 "not release inputs, not a publisher signature and not a "
                 "mathematical certificate."),
    }


def _write_json(path, payload) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("verify", "snapshot", "compare", "evidence"))
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output")
    parser.add_argument("--snapshot")
    parser.add_argument("--directory", action="append", default=[],
                        help="repeatable evidence directory")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        if args.command == "verify":
            result = verify(root)
            ok = not (result["mismatched"] or result["missing"]
                      or result["unlisted"] or result["absent"])
            if args.output:
                _write_json(args.output, result)
            print(("PASS" if ok else "FAIL") + ": "
                  f"{result['checked']} release inputs, "
                  f"{len(result['mismatched'])} mismatched, "
                  f"{len(result['missing'])} missing, "
                  f"{len(result['unlisted'])} unlisted, "
                  f"{len(result['absent'])} absent")
            return 0 if ok else 1
        if args.command == "snapshot":
            if not args.output:
                parser.error("snapshot requires --output")
            payload = snapshot(root)
            _write_json(args.output, payload)
            print(f"PASS: snapshot of {len(payload['files'])} release inputs -> {args.output}")
            return 0
        if args.command == "compare":
            if not args.snapshot:
                parser.error("compare requires --snapshot")
            recorded = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
            result = compare(root, recorded)
            if args.output:
                _write_json(args.output, result)
            stable = result["release_inputs_stable"]
            print(("PASS" if stable else "FAIL") +
                  ": release inputs unchanged during the job"
                  if stable else
                  ": release inputs CHANGED during the job "
                  f"(added={result['added']}, removed={result['removed']}, "
                  f"modified={result['modified']})")
            return 0 if stable else 1
        if not args.output or not args.directory:
            parser.error("evidence requires --output and --directory")
        payload = evidence_manifest(args.directory)
        _write_json(args.output, payload)
        print(f"PASS: {len(payload['files'])} runtime evidence files -> {args.output}")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

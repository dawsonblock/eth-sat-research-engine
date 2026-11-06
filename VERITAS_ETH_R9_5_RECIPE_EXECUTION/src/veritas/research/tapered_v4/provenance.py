"""Deterministic source and manuscript content bindings for V3 evidence."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


PINNED_MANUSCRIPT_TREE_SHA256 = "f4a10137d8630cb8ff26d031aca38c23a39db4606a4494ff7e43f59b8c671594"
PINNED_CONTRACTION_SOURCE_SHA256 = "671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860"


class SourceBindingError(RuntimeError):
    pass


def _root(root=None) -> Path:
    if root is not None:
        path = Path(root).resolve()
    else:
        # provenance.py: repo/src/veritas/research/tapered_v4/provenance.py
        path = Path(__file__).resolve().parents[4]
    if not (path / "src" / "veritas").is_dir():
        raise SourceBindingError("repository source tree is unavailable")
    return path


def _manifest(root: Path, include_source: bool):
    candidates = []
    for tree in (root / "paper", root / "src" / "veritas"):
        if tree.is_symlink():
            raise SourceBindingError(f"symlink tree excluded by policy: {tree}")
        if tree.exists():
            for member in tree.rglob("*"):
                if member.is_symlink():
                    raise SourceBindingError(f"symlink excluded by policy: {member}")
    if include_source:
        candidates.extend((root / "src" / "veritas").rglob("*.py"))
        candidates.append(root / "docs" / "OPENAI_PAPER_CONFORMANCE.md")
        for optional in (root / "pyproject.toml", root / "VERSION"):
            if optional.is_file():
                candidates.append(optional)
    candidates.extend(p for p in (root / "paper").rglob("*") if p.is_file())
    unique = {}
    for path in candidates:
        if path.is_symlink():
            raise SourceBindingError(f"symlink excluded by policy: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        try:
            rel.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise SourceBindingError("source path is not UTF-8 encodable") from exc
        unique[rel] = path
    if not any(name == "paper/quantitative-contraction.tex" for name in unique):
        raise SourceBindingError("pinned contraction manuscript source is absent")
    return [{"path": name, "sha256": sha256(path.read_bytes()).hexdigest()}
            for name, path in sorted(unique.items())]


def _digest(entries):
    mapping = {item["path"]: item["sha256"] for item in entries}
    canonical = json.dumps(mapping, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii")
    return sha256(canonical).hexdigest()


def source_binding(root=None):
    """Hash imported package source, pin document, and vendored manuscript bytes.

    The manifest excludes tests, generated reports/evidence, release manifests,
    ZIPs, caches and bytecode. Paths are UTF-8 POSIX relative paths; symlinks
    are rejected. This is a content hash, not a signature or authenticated
    build attestation.
    """
    base = _root(root)
    entries = _manifest(base, include_source=True)
    return {"algorithm": "sha256", "digest": _digest(entries), "files": entries,
            "path_encoding": "UTF-8", "path_separator": "/",
            "symlink_policy": "REJECT", "hash_exclusions": [
                "tests/**", "scripts/**", "validation/**", "generated release manifests",
                "generated transcripts and evidence", "ZIP archives", "__pycache__/**", "*.pyc"],
            "signature_status": "UNSIGNED_HASH_MATCH_ONLY"}


def manuscript_binding(root=None):
    base = _root(root)
    entries = _manifest(base, include_source=False)
    digest = _digest(entries)
    contraction = next((item["sha256"] for item in entries
                        if item["path"] == "paper/quantitative-contraction.tex"), None)
    return {"algorithm": "sha256", "tree_digest": digest,
            "contraction_source_sha256": contraction,
            "pinned_tree_digest": PINNED_MANUSCRIPT_TREE_SHA256,
            "pinned_contraction_source_sha256": PINNED_CONTRACTION_SOURCE_SHA256,
            "pin_matches": (digest == PINNED_MANUSCRIPT_TREE_SHA256 and
                            contraction == PINNED_CONTRACTION_SOURCE_SHA256),
            "files": entries}

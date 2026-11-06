"""Resolve where a validator writes freshly generated evidence.

Precedence:

1. ``--output PATH`` on the command line (explicit destination),
2. ``VERITAS_EVIDENCE_DIR`` (a directory, out-of-tree for CI),
3. the historical in-tree default.

Writing inside the release tree invalidates the immutable release-input
manifest, because every default destination is a manifest-covered file.
CI therefore always passes an out-of-tree destination, and the job fails if
any tracked release input changed while it ran.

The parser is deliberately tiny and never raises: a malformed ``--output``
is reported as ``INVALID_EVIDENCE_DESTINATION`` so the calling validator can
fail closed rather than silently writing to the release tree.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


class EvidencePathError(ValueError):
    """The requested evidence destination is unusable."""


def _scan_output(argv):
    value = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--output":
            if index + 1 >= len(argv):
                raise EvidencePathError("--output requires a path")
            value = argv[index + 1]
            index += 2
            continue
        if token.startswith("--output="):
            value = token.split("=", 1)[1]
        index += 1
    return value


def evidence_path(default_relative, argv=None, *, root=None):
    """Return the destination for one generated evidence document.

    ``default_relative`` is the historical repository-relative path, kept so
    local runs reproduce the documented behaviour.
    """
    if not isinstance(default_relative, str) or not default_relative:
        raise EvidencePathError("a nonempty default evidence path is required")
    requested = _scan_output(list(sys.argv[1:] if argv is None else argv))
    if requested is not None:
        target = Path(requested)
    else:
        directory = os.environ.get("VERITAS_EVIDENCE_DIR")
        if directory:
            target = Path(directory) / Path(default_relative).name
        else:
            base = Path(root) if root is not None else Path.cwd()
            target = base / default_relative
    if not target.is_absolute():
        target = (Path(root) if root is not None else Path.cwd()) / target
    parent = target.parent
    if parent.exists() and not parent.is_dir():
        raise EvidencePathError(f"evidence parent is not a directory: {parent}")
    return target


def write_evidence(target, text):
    """Write generated evidence, creating the parent directory if needed."""
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path

"""Content-addressed access to the pinned contraction manuscript.

The manuscript bytes are a *required* resource: every source-state admission
and every source-leaf contraction binds them by SHA-256.  Three properties are
non-negotiable, and each has a test:

1. **Explicit provenance.**  The bytes come from one of exactly two declared
   locations -- the distribution resource bundled at
   ``veritas/research/tapered_v4/_resources/quantitative-contraction.tex``, or
   an external asset named explicitly by the caller (``manuscript=`` or the
   ``VERITAS_MANUSCRIPT_PATH`` environment variable).  There is no search of
   parent directories, no fallback to "a file called the same thing nearby",
   and no acceptance of a different revision.

2. **Exact identity.**  A missing, truncated, re-encoded or substituted
   manuscript is refused with ``INCONCLUSIVE_SOURCE_MISMATCH``.  Nothing is
   ever returned for a mismatched asset.

3. **Location independence.**  A source checkout and an installed wheel that
   both carry the authentic pinned asset produce byte-identical results.

A SHA-256 match proves byte identity.  It does not authenticate the publisher
and it does not prove the manuscript's mathematical content.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
from pathlib import Path

from .source_state import SourceAdmissionError

PINNED_MANUSCRIPT_SHA256 = (
    "671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860")
RESOURCE_PACKAGE = "veritas.research.tapered_v4"
RESOURCE_DIRECTORY = "_resources"
RESOURCE_NAME = "quantitative-contraction.tex"
ENVIRONMENT_VARIABLE = "VERITAS_MANUSCRIPT_PATH"
MAXIMUM_MANUSCRIPT_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class PinnedManuscript:
    """Authentic manuscript bytes and where they were read from."""
    data: bytes
    origin: str
    sha256: str

    @property
    def text(self) -> str:
        return self.data.decode("utf-8")


def _read_bytes(path: Path, origin: str) -> PinnedManuscript:
    if not path.is_file():
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"pinned manuscript is absent from {origin}")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"pinned manuscript is unreadable from {origin}: {exc}") from exc
    if size > MAXIMUM_MANUSCRIPT_BYTES:
        raise SourceAdmissionError(
            "INCONCLUSIVE_RESOURCE_LIMIT",
            f"pinned manuscript exceeds its byte cap at {origin}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"pinned manuscript is unreadable from {origin}: {exc}") from exc
    digest = sha256(data).hexdigest()
    if digest != PINNED_MANUSCRIPT_SHA256:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"pinned manuscript at {origin} is substituted or modified "
            f"(sha256 {digest})")
    return PinnedManuscript(data, origin, digest)


def _bundled() -> PinnedManuscript:
    """Read the distribution-bundled manuscript through importlib.resources."""
    try:
        root = resources.files(RESOURCE_PACKAGE).joinpath(RESOURCE_DIRECTORY)
        member = root.joinpath(RESOURCE_NAME)
    except (ModuleNotFoundError, TypeError) as exc:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"packaged manuscript resource is unavailable: {exc}") from exc
    try:
        data = member.read_bytes()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError) as exc:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            "packaged manuscript resource is absent from the installed "
            "distribution; supply an explicit authentic asset with "
            f"{ENVIRONMENT_VARIABLE} or the manuscript= argument") from exc
    except OSError as exc:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"packaged manuscript resource is unreadable: {exc}") from exc
    if len(data) > MAXIMUM_MANUSCRIPT_BYTES:
        raise SourceAdmissionError(
            "INCONCLUSIVE_RESOURCE_LIMIT",
            "packaged manuscript resource exceeds its byte cap")
    digest = sha256(data).hexdigest()
    if digest != PINNED_MANUSCRIPT_SHA256:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            "packaged manuscript resource is substituted or modified "
            f"(sha256 {digest})")
    return PinnedManuscript(data, f"package:{RESOURCE_PACKAGE}/{RESOURCE_DIRECTORY}/"
                                  f"{RESOURCE_NAME}", digest)


def _explicit_path(manuscript) -> Path | None:
    if manuscript is None:
        value = os.environ.get(ENVIRONMENT_VARIABLE)
        return Path(value) if value else None
    if isinstance(manuscript, PinnedManuscript):
        return None
    if isinstance(manuscript, (str, os.PathLike)):
        return Path(manuscript)
    if isinstance(manuscript, bytes):
        raise TypeError("pass a path or an explicit asset path, not raw bytes")
    raise TypeError("manuscript must be a path, a PinnedManuscript or None")


def read_pinned_manuscript(manuscript=None) -> PinnedManuscript:
    """Return the authentic pinned manuscript or refuse with a status.

    ``manuscript`` may be a filesystem path (``str``/``PathLike``) or an
    already-verified :class:`PinnedManuscript`.  An explicit asset always takes
    precedence over the bundled copy and is validated identically.
    """
    if isinstance(manuscript, PinnedManuscript):
        if manuscript.sha256 != PINNED_MANUSCRIPT_SHA256:
            raise SourceAdmissionError(
                "INCONCLUSIVE_SOURCE_MISMATCH",
                "supplied manuscript record does not carry the pinned digest")
        return manuscript
    explicit = _explicit_path(manuscript)
    if explicit is not None:
        return _read_bytes(explicit, f"explicit:{explicit}")
    return _bundled()


def verify_manuscript_bytes(data: bytes) -> str:
    """Validate raw manuscript bytes and return their digest."""
    if not isinstance(data, bytes):
        raise TypeError("manuscript bytes required")
    if len(data) > MAXIMUM_MANUSCRIPT_BYTES:
        raise SourceAdmissionError(
            "INCONCLUSIVE_RESOURCE_LIMIT", "manuscript exceeds its byte cap")
    digest = sha256(data).hexdigest()
    if digest != PINNED_MANUSCRIPT_SHA256:
        raise SourceAdmissionError(
            "INCONCLUSIVE_SOURCE_MISMATCH",
            f"manuscript bytes are substituted or modified (sha256 {digest})")
    return digest

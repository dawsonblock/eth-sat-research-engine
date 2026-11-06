"""Canonical, domain-separated encoding for every VERITAS evidence digest.

Two rules, both testable:

**Canonical form.**  A value is encoded with sorted object keys, no insignificant
whitespace, ASCII-only output, and ``allow_nan=False``.  Re-encoding a decoded
document reproduces the exact bytes, so any two producers that agree on the
value agree on the digest.

**Domain separation.**  A digest is
``sha256(b"VERITAS" || 0x00 || domain || 0x00 || version || 0x00 || payload)``.
Two documents with identical payloads but different domains (or versions) have
different digests, so a certificate digest can never be replayed as a recipe
digest or an entry digest.

A digest proves **byte identity**.  It does not prove provenance, authorship,
mathematical correctness, or that a human approved the contents.  Every
function here says so in its return value.
"""
from __future__ import annotations

import json
from hashlib import sha256

MAGIC = b"VERITAS"
DIGEST_VERSION = 1
MAXIMUM_PAYLOAD_BYTES = 64 * 1024 * 1024

DOMAINS = (
    "source.entry.recipe",
    "source.entry.value",
    "source.leaf.value",
    "source.node",
    "source.context",
    "parent.child.certificate",
    "parent.child.transcript",
    "replay.transcript",
    "evidence.manifest",
)


class CanonicalEncodingError(ValueError):
    """The value has no canonical encoding under this contract."""


def canonical_bytes(value):
    """Deterministic ASCII JSON bytes for ``value``."""
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CanonicalEncodingError(f"value is not canonically encodable: {exc}") from exc
    data = text.encode("ascii")
    if len(data) > MAXIMUM_PAYLOAD_BYTES:
        raise CanonicalEncodingError("payload exceeds the canonical byte cap")
    return data


def _header(domain, version):
    if type(domain) is not str or domain not in DOMAINS:
        raise CanonicalEncodingError(f"unregistered digest domain: {domain!r}")
    if type(version) is not int or version < 1:
        raise CanonicalEncodingError("digest version must be a positive integer")
    return MAGIC + b"\x00" + domain.encode("ascii") + b"\x00" + str(version).encode("ascii") + b"\x00"


def domain_digest(domain, value, *, version=DIGEST_VERSION):
    """Domain-separated SHA-256 of a canonically encoded value."""
    return sha256(_header(domain, version) + canonical_bytes(value)).hexdigest()


def digest_record(domain, value, *, version=DIGEST_VERSION):
    """Digest plus the metadata needed to state what it does and does not prove."""
    return {
        "domain": domain,
        "version": version,
        "algorithm": "sha256",
        "encoding": "canonical-json/ascii/sorted-keys",
        "digest": domain_digest(domain, value, version=version),
        "proves": "byte_identity_of_this_canonical_encoding",
        "does_not_prove": ["provenance", "authorship", "mathematical_correctness",
                           "approval", "freshness_of_any_external_artifact"],
        "trust_class": "HASH_MATCH_UNSIGNED",
    }


def canonical_roundtrip(value):
    """Decode the canonical bytes and re-encode; must be a fixed point."""
    data = canonical_bytes(value)
    return canonical_bytes(json.loads(data))


def is_canonical(document_bytes):
    """True when the bytes are already the canonical encoding of their value."""
    if type(document_bytes) is not bytes:
        raise TypeError("canonical check needs bytes")
    try:
        value = json.loads(document_bytes)
    except (UnicodeError, json.JSONDecodeError):
        return False
    try:
        return canonical_bytes(value) == document_bytes
    except CanonicalEncodingError:
        return False

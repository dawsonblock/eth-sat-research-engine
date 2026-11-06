"""R9.6 regression tests: canonical encoding and fail-closed validators.

The R9.5 validators were structural asserts inside the producers; nothing
checked a *document*.  Feeding a malformed or hostile document could raise
``IndexError``/``TypeError``/``KeyError`` or allocate a deep object graph
before any bound was applied.  These tests pin the R9.6 contract:

* every rejection is a :class:`ValidationRefusal` with an
  ``INVALID_*``/``INCONCLUSIVE_*`` status;
* bounds are applied before ``json.loads`` builds objects;
* unknown critical fields and unknown schemas are refused;
* an inconclusive status can never carry a numerical result;
* no theorem flag can be set by arithmetic success.
"""
import json
import os
import subprocess
import sys
from hashlib import sha256

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, settings, strategies as st

from veritas.research.tapered_v4.canonical import (
    CanonicalEncodingError, DIGEST_VERSION, DOMAINS, canonical_bytes,
    canonical_roundtrip, digest_record, domain_digest, is_canonical)
from veritas.research.tapered_v4.validators import (
    CERTIFICATE_SCHEMA, ENTRY_SCHEMA, LEAF_SCHEMA, MAXIMUM_DOCUMENT_BYTES,
    REPLAY_SCHEMA, ValidationRefusal, decode_document, validate_bytes,
    validate_certificate_document, validate_entry_document,
    validate_leaf_document, validate_replay_document)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_ENTRY = {
    "schema": ENTRY_SCHEMA,
    "status": "EXACT_CREATION_PRECISION_ENTRY",
    "result": [[1, 0]],
    "creation_precision": 3,
    "evaluation_precision": 7,
    "recipe_sha256": "a" * 64,
    "ledger": {"work_units": 12, "counters": {"coefficient_multiplications": 4}},
    "theorem_qualified": False,
}


def refusal_of(callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
    except ValidationRefusal as exc:
        assert exc.status.startswith(("INVALID_", "INCONCLUSIVE_")), exc.status
        return exc
    raise AssertionError("expected a ValidationRefusal")


# --------------------------------------------------------------------------
# canonical encoding
# --------------------------------------------------------------------------

@given(st.recursive(
    st.none() | st.booleans() | st.integers(min_value=-(1 << 63), max_value=1 << 63)
    | st.text(max_size=16),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=8), children, max_size=4),
    max_leaves=24))
@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_canonical_encoding_is_a_fixed_point(value):
    data = canonical_bytes(value)
    assert canonical_bytes(json.loads(data)) == data
    assert is_canonical(data)


def test_domain_separation_changes_the_digest():
    payload = {"a": 1}
    digests = {domain: domain_digest(domain, payload) for domain in DOMAINS}
    assert len(set(digests.values())) == len(DOMAINS)


def test_version_separation_changes_the_digest():
    payload = {"a": 1}
    assert (domain_digest("source.entry.value", payload, version=1)
            != domain_digest("source.entry.value", payload, version=2))


def test_unknown_domain_is_refused():
    with pytest.raises(CanonicalEncodingError):
        domain_digest("unregistered", {})


def test_non_finite_numbers_are_refused():
    with pytest.raises(CanonicalEncodingError):
        canonical_bytes({"x": float("nan")})
    with pytest.raises(CanonicalEncodingError):
        canonical_bytes({"x": float("inf")})


def test_digest_record_states_what_it_does_not_prove():
    record = digest_record("source.leaf.value", {"x": 1})
    assert record["trust_class"] == "HASH_MATCH_UNSIGNED"
    assert "provenance" in record["does_not_prove"]
    assert record["version"] == DIGEST_VERSION


def test_canonical_bytes_match_a_manual_digest():
    value = {"b": [1, 2], "a": "x"}
    payload = b'{"a":"x","b":[1,2]}'
    assert canonical_bytes(value) == payload
    assert domain_digest("source.entry.value", value) == sha256(
        b"VERITAS\x00source.entry.value\x001\x00" + payload).hexdigest()


# --------------------------------------------------------------------------
# bounded decoding
# --------------------------------------------------------------------------

def test_decode_rejects_oversized_document():
    refusal = refusal_of(decode_document, b"x" * (MAXIMUM_DOCUMENT_BYTES + 1))
    assert refusal.status == "INCONCLUSIVE_RESOURCE_LIMIT"


def test_decode_rejects_a_depth_bomb_before_allocating():
    bomb = b"[" * 5000 + b"]" * 5000
    refusal = refusal_of(decode_document, bomb)
    assert refusal.status == "INCONCLUSIVE_RESOURCE_LIMIT"


def test_decode_rejects_duplicate_keys():
    refusal_of(decode_document, b'{"a":1,"a":2}')


def test_decode_rejects_non_finite_literals():
    refusal_of(decode_document, b'{"a":NaN}')
    refusal_of(decode_document, b'{"a":Infinity}')


def test_decode_rejects_invalid_utf8_truncation_and_wrong_types():
    refusal_of(decode_document, b"\xff\xfe")
    refusal_of(decode_document, b'{"a":')
    refusal_of(decode_document, b"]")
    refusal_of(decode_document, 42)
    refusal_of(decode_document, None)


@pytest.mark.parametrize("mutate", ["unknown_field", "missing_field", "bool_int",
                                    "negative", "bad_digest", "bad_status",
                                    "wrong_schema"])
def test_entry_validator_rejects_every_mutation(mutate):
    document = json.loads(json.dumps(VALID_ENTRY))
    if mutate == "unknown_field":
        document["extra"] = 1
    elif mutate == "missing_field":
        del document["recipe_sha256"]
    elif mutate == "bool_int":
        document["creation_precision"] = True
    elif mutate == "negative":
        document["creation_precision"] = 0
    elif mutate == "bad_digest":
        document["recipe_sha256"] = "zz"
    elif mutate == "bad_status":
        document["status"] = "TOTALLY_FINE"
    else:
        document["schema"] = "VERITAS_SOURCE_ENTRY_V0"
    refusal_of(validate_bytes, json.dumps(document).encode(), schema=ENTRY_SCHEMA)


def test_inconclusive_entry_must_not_carry_a_result():
    document = dict(VALID_ENTRY, status="INCONCLUSIVE_RESOURCE_LIMIT")
    refusal_of(validate_entry_document, document)


def test_exact_entry_must_carry_its_result():
    document = {k: v for k, v in VALID_ENTRY.items() if k != "result"}
    refusal_of(validate_entry_document, document)


def test_theorem_promotion_is_refused():
    for flag in ("theorem_qualified", "theorem_mode_enabled",
                 "subexponential_runtime_proven"):
        document = dict(VALID_ENTRY, **{flag: True})
        refusal_of(validate_entry_document, document)


def test_leaf_document_validation_and_refusal():
    document = {"schema": LEAF_SCHEMA,
                "status": "EXACT_SOURCE_LEAF_MODULAR_CONTRACTION",
                "result": [[1, 0, 0, 0]], "precision": 1, "s": 2, "M": 0,
                "leaf_threshold": 2, "theorem_mode_enabled": False,
                "ledger": {"work_units": 5, "counters": {}}}
    assert validate_leaf_document(document) is document
    bad = dict(document, status="INCONCLUSIVE_SOURCE_MISMATCH")
    refusal_of(validate_leaf_document, bad)
    del bad["result"]
    assert validate_leaf_document(bad) is bad


def test_certificate_cardinality_and_coverage_are_cross_checked():
    from tests.test_r96_parent_child import build_certificate_fixture  # noqa
    document = build_certificate_fixture()
    assert validate_certificate_document(document) is document
    refusal_of(validate_certificate_document,
               dict(document, modes=dict(document["modes"], cardinality=99)))
    refusal_of(validate_certificate_document,
               dict(document, coverage={"points_checked": 5,
                                        "points_required": 4}))
    refusal_of(validate_certificate_document,
               dict(document, theorem_scope={"theorem_mode_enabled": True,
                                             "scope": "THEOREM"}))


def test_replay_document_validation():
    document = {"schema": REPLAY_SCHEMA, "valid": True,
                "certificate_digest": "b" * 64,
                "events": [{"previous": "0" * 64, "payload": {}, "hash": "c" * 64}]}
    assert validate_replay_document(document) is document
    refusal_of(validate_replay_document, dict(document, valid="yes"))


@given(st.binary(max_size=4096))
@settings(max_examples=120, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_arbitrary_bytes_never_raise_a_builtin_exception(data):
    """Fuzz: decoding and validation only ever refuse, never crash."""
    try:
        decode_document(data)
    except ValidationRefusal:
        return
    except (IndexError, TypeError, KeyError, AttributeError, MemoryError,
            RecursionError) as exc:  # pragma: no cover - the failure we forbid
        raise AssertionError(f"builtin exception escaped: {exc!r}")
    # If it decoded, the entry validator must also be total.
    try:
        validate_entry_document(json.loads(data))
    except ValidationRefusal:
        pass


@given(st.dictionaries(st.text(max_size=8),
                       st.none() | st.booleans() | st.integers() | st.text(max_size=8),
                       max_size=8))
@settings(max_examples=80, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_arbitrary_documents_are_refused_or_accepted_but_never_crash(document):
    try:
        validate_entry_document(document)
    except ValidationRefusal:
        return


def test_validation_is_identical_under_optimized_python():
    payload = json.dumps(dict(VALID_ENTRY, extra=1)).encode()
    script = (
        "import json,sys\n"
        "from veritas.research.tapered_v4.validators import validate_bytes, "
        "ValidationRefusal\n"
        "try:\n"
        "    validate_bytes(sys.stdin.buffer.read(), schema='VERITAS_SOURCE_ENTRY_RESULT_V1')\n"
        "    print('ACCEPTED')\n"
        "except ValidationRefusal as exc:\n"
        "    print('REFUSED', exc.status)\n")
    outputs = []
    for flags in ([], ["-O"]):
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
        result = subprocess.run([sys.executable] + flags + ["-c", script],
                                input=payload, capture_output=True, env=env,
                                timeout=120)
        assert result.returncode == 0, result.stderr
        outputs.append(result.stdout.decode().strip())
    assert outputs[0] == outputs[1] == "REFUSED INVALID_DOCUMENT"

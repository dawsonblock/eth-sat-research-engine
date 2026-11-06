"""Large creation coefficients retain bounded, independently readable bytes."""

from dataclasses import replace
import json

import pytest

from veritas.research.bounded_integer_encoding import TAG
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, _entry
from veritas.research.parent_child_r98.model import canonical, decode
from veritas.research.tapered_v4.source_recipes import (
    EntryBudget, EntryLimits, compile_entry, evaluate_source_entry, make_reference,
)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_old_bytes_and_decimal_limit_are_preserved():
    value = {"small": [0, 1, -3, 10**400 - 1], "flag": True}
    assert canonical(value) == raw(value)
    assert decode(canonical(value)) == value
    with pytest.raises(ValueError, match="integer byte cap"):
        decode(b"1" + b"0" * 400)


@pytest.mark.parametrize("number", [10**400, (1 << 1408) - 84, (1 << 65536) - 1],
                         ids=["threshold", "packet", "bit-limit"])
def test_large_unsigned_integer_has_one_canonical_round_trip(number):
    encoded = canonical({"coefficient": number})
    wire = json.loads(encoded)
    assert wire["coefficient"] == {TAG: format(number, "x")}
    assert decode(encoded) == {"coefficient": number}
    assert canonical(decode(encoded)) == encoded


@pytest.mark.parametrize("digits", [
    "", "0", "1", "0" + format(10**400, "x"),
    format(10**400, "x").upper(), "0x" + format(10**400, "x"),
    "-" + format(10**400, "x"), True, 7, ["abc"],
    "1" + "0" * 16384,
], ids=["empty", "zero", "small", "leading-zero", "upper", "prefix",
        "negative", "bool", "number", "array", "overflow"])
def test_bad_or_oversized_hex_tags_are_rejected(digits):
    with pytest.raises(ValueError):
        decode(raw({TAG: digits}))


def test_tag_field_shape_and_duplicate_keys_are_rejected():
    digits = format(10**400, "x")
    with pytest.raises(ValueError, match="tag fields"):
        decode(raw({TAG: digits, "extra": 1}))
    with pytest.raises(ValueError, match="duplicate"):
        decode((f'{{"{TAG}":"{digits}","{TAG}":"{digits}"}}').encode())
    with pytest.raises(ValueError, match="reserved"):
        canonical({TAG: digits})
    with pytest.raises(ValueError, match="bit cap"):
        canonical(1 << 65536)


def packet_reference(precision=1408):
    coefficient = (1 << precision) - 84
    return make_reference(
        kind="packet", arity=2, creation_precision=precision,
        defining_polynomial=7, jet_length=1,
        data=[[0], [1], [[[[coefficient, 0]]]], [], []],
        limits=EntryLimits(max_precision_bits=65536),
    )


def test_tagged_packet_coefficient_has_independent_creation_lift_semantics():
    ref = packet_reference()
    assert TAG.encode() in ref.description
    limits = EntryLimits(max_precision_bits=65536)
    result = evaluate_source_entry(ref, (1, 1), precision=1600, limits=limits)["result"]
    assert result == (((1 << 1408) - 84, 0),)
    assert result != (((1 << 1600) - 84, 0),)
    independent = ReferenceArithmetic(1600, 7, 1, 100_000, max_precision_bits=65536)
    assert _entry(ref, (1, 1), independent) == result
    with pytest.raises(ValueError):
        compile_entry(ref, EntryBudget(EntryLimits()))


@pytest.mark.parametrize("mutation", ["uppercase", "small", "creation_precision", "bool", "decimal"])
def test_production_and_independent_recipe_decoders_reject_corrupt_encoding(mutation):
    ref = packet_reference()
    payload = json.loads(ref.description)
    coordinate = payload["data"][2][0][0][0]
    if mutation == "uppercase":
        coordinate[0][TAG] = coordinate[0][TAG].upper()
    elif mutation == "small":
        coordinate[0][TAG] = "ff"
    elif mutation == "creation_precision":
        payload["creation_precision"] = 1350
        ref = replace(ref, creation_precision=1350)
    elif mutation == "bool":
        coordinate[0] = True
    else:
        coordinate[0] = (1 << 1408) - 84
    corrupt = replace(ref, description=raw(payload))
    with pytest.raises(ValueError):
        compile_entry(corrupt, EntryBudget(EntryLimits(max_precision_bits=65536)))
    independent = ReferenceArithmetic(1600, 7, 1, 100_000, max_precision_bits=65536)
    with pytest.raises(ValueError):
        _entry(corrupt, (1, 1), independent)

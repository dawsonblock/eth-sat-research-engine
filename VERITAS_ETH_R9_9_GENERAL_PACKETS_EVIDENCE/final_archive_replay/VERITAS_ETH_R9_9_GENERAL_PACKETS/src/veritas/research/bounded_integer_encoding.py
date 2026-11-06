"""Canonical bounded integers for high-precision finite evidence.

Decimal JSON integers retain their existing 400-character limit. Nonnegative
integers needing more decimal digits use the reserved single-field object
``{"$veritas_uint_hex": "<minimal lowercase hexadecimal>"}``. This is a wire
representation only: arithmetic still receives integers, with at most 65536
bits and the caller's narrower creation-precision checks.
"""

import json


TAG = "$veritas_uint_hex"
DECIMAL_LIMIT = 10**400
NEGATIVE_DECIMAL_LIMIT = -(10**399)
MAX_BITS = 65536


def integer_wire_tree(value):
    """Preserve legacy bytes for small integers and encode large residues."""
    if type(value) is int:
        if value >= DECIMAL_LIMIT:
            if value.bit_length() > MAX_BITS:
                raise ValueError("hex integer bit cap")
            return {TAG: format(value, "x")}
        if value <= NEGATIVE_DECIMAL_LIMIT:
            raise ValueError("negative decimal integer byte cap")
        return value
    if type(value) in (list, tuple):
        return [integer_wire_tree(item) for item in value]
    if type(value) is dict:
        if TAG in value:
            raise ValueError("reserved hexadecimal integer tag")
        return {key: integer_wire_tree(item) for key, item in value.items()}
    return value


def canonical_integer_json(value):
    return json.dumps(
        integer_wire_tree(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def decode_integer_object(value, *, max_bits=MAX_BITS):
    """Decode one already duplicate-checked JSON object, with bounded work."""
    if TAG not in value:
        return value
    if set(value) != {TAG}:
        raise ValueError("hexadecimal integer tag fields")
    digits = value[TAG]
    if (
        type(max_bits) is not int or not 1 <= max_bits <= MAX_BITS
        or type(digits) is not str or not digits
        or len(digits) > (max_bits + 3) // 4
        or digits[0] == "0"
        or any(c not in "0123456789abcdef" for c in digits)
    ):
        raise ValueError("noncanonical or oversized hexadecimal integer")
    integer = int(digits, 16)
    if integer < DECIMAL_LIMIT or integer.bit_length() > max_bits:
        raise ValueError("hexadecimal integer threshold or bit cap")
    return integer

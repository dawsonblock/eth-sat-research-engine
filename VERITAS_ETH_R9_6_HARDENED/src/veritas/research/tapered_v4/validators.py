"""Total, fail-closed validators for every public evidence document.

Guarantees, each with a test:

* **Totality.**  A validator never raises ``IndexError``, ``TypeError``,
  ``KeyError``, ``AttributeError`` or ``MemoryError`` on hostile input.  It
  either returns a normalised document or raises :class:`ValidationRefusal`
  carrying an ``INVALID_*``/``INCONCLUSIVE_*`` status.
* **Pre-decode bounds.**  Byte length, structural nesting depth, structural
  node count and integer magnitude are checked *before* ``json.loads`` builds
  any object, so a 10 MB ``[[[[...`` payload is refused without allocating a
  deep object graph.
* **Unknown critical fields are rejected**, not ignored.  A document that
  carries a field this version does not understand cannot be silently
  down-interpreted.
* **Schema versions are explicit.**  An unknown ``schema`` is refused.
* **No accidental promotion.**  A document whose status begins with
  ``INCONCLUSIVE`` must not carry a numerical result, and no document may set a
  theorem-qualified flag from arithmetic success alone.
"""
from __future__ import annotations

import json

MAXIMUM_DOCUMENT_BYTES = 16 * 1024 * 1024
MAXIMUM_DEPTH = 32
MAXIMUM_NODES = 2_000_000
MAXIMUM_INTEGER_BITS = 1 << 16
MAXIMUM_STRING_BYTES = 4_096
MAXIMUM_ARRAY = 1_000_000

ENTRY_SCHEMA = "VERITAS_SOURCE_ENTRY_RESULT_V1"
LEAF_SCHEMA = "VERITAS_SOURCE_LEAF_RESULT_V1"
CERTIFICATE_SCHEMA = "VERITAS_PARENT_CHILD_CERTIFICATE_V1"
REPLAY_SCHEMA = "VERITAS_REPLAY_V1"
KNOWN_SCHEMAS = (ENTRY_SCHEMA, LEAF_SCHEMA, CERTIFICATE_SCHEMA, REPLAY_SCHEMA)

THEOREM_FLAGS = (
    "theorem_qualified",
    "theorem_mode_enabled",
    "theorem_schedule_verified",
    "source_schedule_theorem_proven",
    "entry_cost_theorem_proven",
    "executable_refinement_proven",
    "uniform_complexity_proven",
    "subexponential_runtime_proven",
    "packing_proven",
    "complexity_proven",
)


class ValidationRefusal(ValueError):
    """A document was refused.  ``status`` is always an INVALID_*/INCONCLUSIVE_*."""

    def __init__(self, status, reason, path=""):
        super().__init__(f"{path}: {reason}" if path else reason)
        self.status = status
        self.reason = reason
        self.path = path


def _refuse(reason, path="", status="INVALID_DOCUMENT"):
    raise ValidationRefusal(status, reason, path)


def _scan_structure(text):
    """Count nesting depth and structural tokens without building objects."""
    depth = 0
    maximum = 0
    nodes = 1
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            nodes += 1
            maximum = max(maximum, depth)
            if maximum > MAXIMUM_DEPTH:
                _refuse("document nesting depth exceeds the cap",
                        status="INCONCLUSIVE_RESOURCE_LIMIT")
            if nodes > MAXIMUM_NODES:
                _refuse("document node count exceeds the cap",
                        status="INCONCLUSIVE_RESOURCE_LIMIT")
        elif character in "]}":
            depth -= 1
            if depth < 0:
                _refuse("unbalanced document brackets")
        elif character == ",":
            nodes += 1
            if nodes > MAXIMUM_NODES:
                _refuse("document node count exceeds the cap",
                        status="INCONCLUSIVE_RESOURCE_LIMIT")
    if in_string or depth != 0:
        _refuse("truncated or unbalanced document")


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            _refuse(f"duplicate document field {key!r}")
        seen[key] = value
    return seen


def _reject_constant(name):
    _refuse(f"non-finite number {name} is not permitted")


def decode_document(data, *, label="document"):
    """Bounded decode of JSON bytes.  Never raises a builtin exception."""
    if isinstance(data, str):
        data = data.encode("utf-8", "strict") if data.isascii() else None
        if data is None:
            _refuse("document must be ASCII JSON", label)
    if not isinstance(data, (bytes, bytearray)):
        _refuse("document must be bytes", label)
    if len(data) > MAXIMUM_DOCUMENT_BYTES:
        _refuse("document exceeds the byte cap", label,
                status="INCONCLUSIVE_RESOURCE_LIMIT")
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        _refuse("document is not valid UTF-8", label)
    _scan_structure(text)
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates,
                          parse_constant=_reject_constant)
    except ValidationRefusal:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        _refuse(f"document is not valid JSON: {exc}", label)


def require_mapping(value, *, required, optional=(), label):
    if not isinstance(value, dict):
        _refuse("mapping required", label)
    keys = set(value)
    missing = set(required) - keys
    if missing:
        _refuse(f"missing required field(s) {sorted(missing)}", label)
    unknown = keys - set(required) - set(optional)
    if unknown:
        _refuse(f"unknown critical field(s) {sorted(unknown)}", label)
    return value


def require_int(value, *, low, high, label):
    if type(value) is not int:
        _refuse("integer required", label)
    if value < low or value > high:
        _refuse(f"integer outside [{low}, {high}]", label)
    if value.bit_length() > MAXIMUM_INTEGER_BITS:
        _refuse("integer magnitude exceeds the cap", label,
                status="INCONCLUSIVE_RESOURCE_LIMIT")
    return value


def require_bool(value, *, label):
    if type(value) is not bool:
        _refuse("boolean required", label)
    return value


def require_string(value, *, label, maximum=MAXIMUM_STRING_BYTES):
    if type(value) is not str:
        _refuse("string required", label)
    if len(value) > maximum:
        _refuse("string exceeds the length cap", label,
                status="INCONCLUSIVE_RESOURCE_LIMIT")
    return value


def require_array(value, *, label, maximum=MAXIMUM_ARRAY):
    if type(value) is not list:
        _refuse("array required", label)
    if len(value) > maximum:
        _refuse("array exceeds the length cap", label,
                status="INCONCLUSIVE_RESOURCE_LIMIT")
    return value


def require_status(value, *, label):
    text = require_string(value, label=label, maximum=128)
    allowed_prefixes = ("EXACT_", "INCONCLUSIVE_", "INVALID_", "FINITE_",
                        "PARTIAL_", "SOURCE_", "NECESSARY_", "VALID_")
    if not text.startswith(allowed_prefixes):
        _refuse(f"unknown status vocabulary {text!r}", label)
    return text


def require_jet(value, *, extension_degree, jet_length, modulus, label):
    """One creation-ring element: ``jet_length`` rows of ``extension_degree``."""
    rows = require_array(value, label=label, maximum=jet_length)
    if len(rows) != jet_length:
        _refuse(f"jet must have {jet_length} coordinate rows", label)
    for index, row in enumerate(rows):
        coefficients = require_array(row, label=f"{label}[{index}]",
                                     maximum=extension_degree)
        if len(coefficients) != extension_degree:
            _refuse(f"row must have {extension_degree} coefficients",
                    f"{label}[{index}]")
        for position, coefficient in enumerate(coefficients):
            require_int(coefficient, low=0, high=modulus - 1,
                        label=f"{label}[{index}][{position}]")
    return rows


def require_ledger(value, *, label):
    mapping = require_mapping(
        value,
        required=("work_units", "counters"),
        optional=("coefficients", "notes", "elapsed_seconds",
                  "complete_bit_work", "hard_memory_limit_enforced",
                  "limitations"),
        label=label)
    require_int(mapping["work_units"], low=0, high=1 << 62, label=f"{label}.work_units")
    counters = require_mapping(mapping["counters"], required=(),
                               optional=tuple(mapping["counters"]),
                               label=f"{label}.counters")
    for name, amount in counters.items():
        require_string(name, label=f"{label}.counters key", maximum=128)
        require_int(amount, low=0, high=1 << 62,
                    label=f"{label}.counters.{name}")
    return mapping


def _reject_promotion(document, label):
    for flag in THEOREM_FLAGS:
        if flag in document and document[flag] is True:
            _refuse(f"theorem flag {flag} must not be set by this document",
                    label)


def validate_entry_document(document):
    require_mapping(document,
                    required=("status", "creation_precision",
                              "evaluation_precision", "recipe_sha256", "ledger"),
                    optional=("result", "theorem_qualified"),
                    label="entry")
    status = require_status(document["status"], label="entry.status")
    creation = require_int(document["creation_precision"], low=1, high=1024,
                           label="entry.creation_precision")
    evaluation = require_int(document["evaluation_precision"], low=creation,
                             high=1024, label="entry.evaluation_precision")
    require_string(document["recipe_sha256"], label="entry.recipe_sha256",
                   maximum=64)
    if len(document["recipe_sha256"]) != 64:
        _refuse("recipe digest must be 64 hex characters", "entry.recipe_sha256")
    require_ledger(document["ledger"], label="entry.ledger")
    _reject_promotion(document, "entry")
    if status.startswith("INCONCLUSIVE") and "result" in document:
        _refuse("an inconclusive entry must not carry a result", "entry.result")
    if status.startswith("EXACT_") and "result" not in document:
        _refuse("an exact entry must carry its result", "entry.result")
    return document


def validate_leaf_document(document, *, context=None):
    required = ("status", "ledger")
    optional = ("schema", "result", "precision", "s", "M", "leaf_threshold",
                "independent_variable_elimination_checked", "recipe_hashes",
                "theorem_mode_enabled", "entry_cost_theorem_proven",
                "active_recursion_implemented", "executable_refinement_proven",
                "reason")
    require_mapping(document, required=required, optional=optional,
                    label="leaf")
    status = require_status(document["status"], label="leaf.status")
    require_ledger(document["ledger"], label="leaf.ledger")
    _reject_promotion(document, "leaf")
    if status.startswith("INCONCLUSIVE"):
        if "result" in document:
            _refuse("an inconclusive leaf must not carry a result", "leaf.result")
        return document
    if "result" not in document:
        _refuse("a successful leaf must carry its result", "leaf.result")
    for name in ("precision", "s", "M", "leaf_threshold"):
        require_int(document[name], low=0, high=1 << 62, label=f"leaf.{name}")
    if context is not None:
        require_jet(document["result"],
                    extension_degree=context.extension_degree,
                    jet_length=context.jet_length,
                    modulus=1 << document["precision"],
                    label="leaf.result")
    return document


def validate_certificate_document(document):
    require_mapping(
        document,
        required=("schema", "claim", "parent", "modes", "children",
                  "coverage", "budgets", "theorem_scope"),
        optional=("refusals", "digest", "trust_class", "notes", "points"),
        label="certificate")
    if document["schema"] != CERTIFICATE_SCHEMA:
        _refuse(f"unknown certificate schema {document['schema']!r}",
                "certificate.schema")
    require_string(document["claim"], label="certificate.claim", maximum=128)
    require_mapping(document["parent"],
                    required=("network_digest", "source_context_digest",
                              "edges", "depth", "parameters"),
                    optional=("port_order", "row_port_order", "column_port_order",
                              "maximum_degree", "precision"),
                    label="certificate.parent")
    modes = require_mapping(document["modes"],
                            required=("domains", "enumeration_rule"),
                            optional=("exponent_bound", "point_domain_count"),
                            label="certificate.modes")
    domains = require_array(modes["domains"],
                            label="certificate.modes.domains", maximum=4096)
    for index, entry in enumerate(domains):
        label = f"certificate.modes.domains[{index}]"
        mapping = require_mapping(
            entry,
            required=("node", "point_index", "ordered_tuples", "cardinality"),
            optional=("mode_count", "weights", "packets", "target_groups",
                      "source_groups", "mode_set_digest"),
            label=label)
        require_int(mapping["node"], low=-(1 << 40), high=1 << 40,
                    label=f"{label}.node")
        require_int(mapping["point_index"], low=0, high=1 << 40,
                    label=f"{label}.point_index")
        ordered = require_array(mapping["ordered_tuples"],
                                label=f"{label}.ordered_tuples",
                                maximum=1_000_000)
        require_int(mapping["cardinality"], low=0, high=1_000_000,
                    label=f"{label}.cardinality")
        if len(ordered) != mapping["cardinality"]:
            _refuse("declared cardinality differs from the enumerated tuple count",
                    f"{label}.cardinality")
        for item_index, item in enumerate(ordered):
            if type(item) is not list:
                _refuse("ordered tuple must be an array",
                        f"{label}.ordered_tuples[{item_index}]")
            for position, exponent in enumerate(item):
                require_int(exponent, low=0, high=1 << 16,
                            label=f"{label}.ordered_tuples[{item_index}][{position}]")
    children = require_array(document["children"], label="certificate.children",
                             maximum=1_000_000)
    coverage = require_mapping(document["coverage"],
                               required=("points_checked", "points_required"),
                               optional=("classification", "points_skipped"),
                               label="certificate.coverage")
    require_int(coverage["points_checked"], low=0, high=1 << 40,
                label="certificate.coverage.points_checked")
    require_int(coverage["points_required"], low=0, high=1 << 40,
                label="certificate.coverage.points_required")
    if coverage["points_checked"] > coverage["points_required"]:
        _refuse("checked points exceed required points",
                "certificate.coverage.points_checked")
    budgets = require_mapping(document["budgets"],
                              required=("max_work", "work_used"),
                              optional=("max_points", "max_children",
                                        "max_enumeration", "limits"),
                              label="certificate.budgets")
    require_int(budgets["max_work"], low=1, high=1 << 40,
                label="certificate.budgets.max_work")
    require_int(budgets["work_used"], low=0, high=1 << 40,
                label="certificate.budgets.work_used")
    scope = require_mapping(document["theorem_scope"],
                            required=("theorem_mode_enabled", "scope"),
                            optional=("omitted_modes", "hypotheses"),
                            label="certificate.theorem_scope")
    if scope["theorem_mode_enabled"] is not False:
        _refuse("a finite certificate must not enable theorem mode",
                "certificate.theorem_scope.theorem_mode_enabled")
    if "points" in document:
        records = require_array(document["points"], label="certificate.points",
                                maximum=1_000_000)
        for index, record in enumerate(records):
            mapping = require_mapping(
                record,
                required=("node", "point_index", "precision", "tuple_count",
                          "parent_value", "tuple_sum", "identity_holds"),
                optional=("point", "multiplicity", "terms"),
                label=f"certificate.points[{index}]")
            require_int(mapping["node"], low=-(1 << 40), high=1 << 40,
                        label=f"certificate.points[{index}].node")
            require_int(mapping["point_index"], low=0, high=1 << 40,
                        label=f"certificate.points[{index}].point_index")
            require_int(mapping["tuple_count"], low=0, high=1 << 40,
                        label=f"certificate.points[{index}].tuple_count")
            require_bool(mapping["identity_holds"],
                         label=f"certificate.points[{index}].identity_holds")
    _reject_promotion(document, "certificate")
    return document


def validate_replay_document(document):
    require_mapping(document,
                    required=("schema", "valid", "certificate_digest"),
                    optional=("status", "reason", "events", "theorem_mode_enabled"),
                    label="replay")
    if document["schema"] != REPLAY_SCHEMA:
        _refuse(f"unknown replay schema {document['schema']!r}", "replay.schema")
    require_bool(document["valid"], label="replay.valid")
    require_string(document["certificate_digest"],
                   label="replay.certificate_digest", maximum=64)
    if "events" in document:
        events = require_array(document["events"], label="replay.events",
                               maximum=1_000_000)
        for index, event in enumerate(events):
            require_mapping(event, required=("previous", "payload", "hash"),
                            label=f"replay.events[{index}]")
    _reject_promotion(document, "replay")
    return document


VALIDATORS = {
    ENTRY_SCHEMA: validate_entry_document,
    LEAF_SCHEMA: validate_leaf_document,
    CERTIFICATE_SCHEMA: validate_certificate_document,
    REPLAY_SCHEMA: validate_replay_document,
}


def validate_bytes(data, *, schema, **kwargs):
    """Decode and validate one document, mapping every failure to a refusal."""
    document = decode_document(data, label=schema)
    if not isinstance(document, dict):
        _refuse("mapping document required", schema)
    declared = document.get("schema")
    if declared is not None and declared != schema:
        _refuse(f"declared schema {declared!r} does not match {schema!r}",
                f"{schema}.schema")
    validator = VALIDATORS.get(schema)
    if validator is None:
        _refuse(f"no validator for schema {schema!r}", schema)
    return validator(document, **kwargs)

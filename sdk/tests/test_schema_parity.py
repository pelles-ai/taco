"""Parity between the models in ``taco.schemas`` and ``spec/schemas/*.json``.

The JSON Schemas are the source of truth (ADR-0002, SPEC-003 §2.1). These
tests fail when a model drifts from its schema and list every mismatch by
path, so the fix is to change the model until the list is empty:

1. Structural parity: each model's ``model_json_schema(by_alias=True)`` is
   diffed against its spec file (required sets, types and nullability,
   enums, formats, bounds, array sizes, nested objects, unknown-property
   handling and defaults).
2. Behavioural parity: the website's example payloads, and mutations of
   them, are run through both a JSON Schema validator (with ``date`` and
   ``date-time`` format checks switched on) and the models. Both must
   agree, and a valid payload must survive ``model_validate`` followed by
   ``model_dump(mode="json", by_alias=True, exclude_none=True)`` unchanged.
"""

from __future__ import annotations

import calendar
import copy
import json
import re
import typing
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from jsonschema import FormatChecker
from jsonschema.validators import validator_for
from pydantic import BaseModel, Field, ValidationError

from taco.schemas import SCHEMA_MODELS, DateString, SchemaModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO_ROOT / "spec" / "schemas"
EXAMPLES_DIR = REPO_ROOT / "website" / "src" / "data" / "schema-examples"

SCHEMA_IDS = sorted(SCHEMA_MODELS)

Schema = dict[str, Any]


# ---------------------------------------------------------------------------
# Structural diff: spec JSON Schema vs model_json_schema()
# ---------------------------------------------------------------------------

# Keywords compared value-for-value between spec and model.
_COMPARED = (
    "type",
    "enum",
    "const",
    "format",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
)
# Keywords walked structurally.
_STRUCTURAL = frozenset({"properties", "required", "items", "additionalProperties", "anyOf"})
# Keywords with no validation effect.
_ANNOTATIONS = frozenset(
    {
        "title",
        "description",
        "default",
        "examples",
        "$comment",
        "$schema",
        "$id",
        "$defs",
        "deprecated",
        "readOnly",
        "writeOnly",
    }
)
_UNDERSTOOD = _ANNOTATIONS | _STRUCTURAL | set(_COMPARED)
_NULL = {"type": "null"}


def _resolve(node: Schema, root: Schema) -> Schema:
    """Follow local ``$ref``s, keeping any sibling keywords."""
    while "$ref" in node:
        ref = node["$ref"]
        assert ref.startswith("#/"), f"only local $refs are supported, got {ref!r}"
        target: Any = root
        for part in ref[2:].split("/"):
            target = target[part]
        node = {**target, **{k: v for k, v in node.items() if k != "$ref"}}
    return node


def _split_null(node: Schema, root: Schema) -> tuple[Schema, bool]:
    """Strip a null branch (Pydantic renders ``X | None`` as anyOf [X, null])."""
    node = _resolve(node, root)
    nullable = False
    if "anyOf" in node and _NULL in node["anyOf"]:
        nullable = True
        rest = [branch for branch in node["anyOf"] if branch != _NULL]
        node = {k: v for k, v in node.items() if k != "anyOf"}
        if len(rest) == 1:
            node = {**node, **_resolve(rest[0], root)}
        else:
            node["anyOf"] = rest
    types = node.get("type")
    if isinstance(types, list) and "null" in types:
        nullable = True
        rest_types = [t for t in types if t != "null"]
        node = {**node, "type": rest_types[0] if len(rest_types) == 1 else rest_types}
    return node, nullable


def _normalised(keyword: str, value: Any) -> Any:
    if value is None:
        return None
    if keyword == "type":
        return frozenset([value] if isinstance(value, str) else value)
    if keyword == "enum":
        return sorted(json.dumps(v, sort_keys=True) for v in value)
    return value


def _is_object(node: Schema) -> bool:
    return node.get("type") == "object" or "properties" in node


def _nested_model(annotation: Any) -> type[BaseModel] | None:
    """The model class inside an annotation such as ``list[Foo] | None``."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in typing.get_args(annotation):
        found = _nested_model(arg)
        if found is not None:
            return found
    return None


class _SchemaDiff:
    def __init__(self, spec_root: Schema, model_root: Schema) -> None:
        self.spec_root = spec_root
        self.model_root = model_root
        self.mismatches: list[str] = []

    def report(self, path: str, message: str) -> None:
        self.mismatches.append(f"{path}: {message}")

    def compare(
        self,
        spec: Schema,
        model: Schema,
        path: str,
        model_cls: type[BaseModel] | None,
        *,
        optional: bool = False,
    ) -> None:
        spec, spec_nullable = _split_null(spec, self.spec_root)
        model, model_nullable = _split_null(model, self.model_root)
        # An optional field may be None in Python: exclude_none drops it on dump.
        if model_nullable and not spec_nullable and not optional:
            self.report(path, "model accepts null but the spec does not")
        if spec_nullable and not model_nullable:
            self.report(path, "spec accepts null but the model does not")

        for side, node in (("spec", spec), ("model", model)):
            unknown = sorted(set(node) - _UNDERSTOOD)
            if unknown:
                self.report(
                    path, f"{side} uses keywords this parity test does not check: {unknown}"
                )

        for keyword in _COMPARED:
            spec_value, model_value = spec.get(keyword), model.get(keyword)
            if _normalised(keyword, spec_value) != _normalised(keyword, model_value):
                self.report(path, f"{keyword}: spec={spec_value!r} model={model_value!r}")

        if "anyOf" in spec or "anyOf" in model:
            spec_any, model_any = spec.get("anyOf", []), model.get("anyOf", [])
            if len(spec_any) != len(model_any):
                self.report(path, f"anyOf: spec={spec_any!r} model={model_any!r}")
            else:
                for i, (s, m) in enumerate(zip(spec_any, model_any, strict=True)):
                    self.compare(s, m, f"{path}.anyOf[{i}]", None)

        if _is_object(spec) or _is_object(model):
            self._compare_object(spec, model, path, model_cls)

        if "items" in spec or "items" in model:
            if "items" in spec and "items" in model:
                self.compare(spec["items"], model["items"], f"{path}[]", model_cls)
            else:
                self.report(path, f"items: spec={spec.get('items')!r} model={model.get('items')!r}")

    def _compare_object(
        self, spec: Schema, model: Schema, path: str, model_cls: type[BaseModel] | None
    ) -> None:
        spec_props, model_props = spec.get("properties", {}), model.get("properties", {})
        spec_required = set(spec.get("required", []))
        model_required = set(model.get("required", []))

        for name in sorted(spec_required - model_required):
            self.report(f"{path}.{name}", "required by the spec but optional in the model")
        for name in sorted(model_required - spec_required):
            self.report(f"{path}.{name}", "required by the model but optional in the spec")
        for name in sorted(spec_props.keys() - model_props.keys()):
            self.report(f"{path}.{name}", "in the spec but missing from the model")
        for name in sorted(model_props.keys() - spec_props.keys()):
            self.report(f"{path}.{name}", "in the model but not in the spec")

        if model_cls is None:
            self.report(path, "object schema could not be mapped to a model class")
            fields = {}
        else:
            fields = {(f.alias or n): f for n, f in model_cls.model_fields.items()}

        for name in sorted(spec_props.keys() & model_props.keys()):
            field = fields.get(name)
            if field is not None and not field.is_required():
                default = field.get_default(call_default_factory=True)
                spec_default = _resolve(spec_props[name], self.spec_root).get("default")
                if default != spec_default:
                    self.report(
                        f"{path}.{name}",
                        f"model default {default!r} is not the spec's ({spec_default!r}); "
                        "an unset optional field must stay None so exclude_none omits it",
                    )
            self.compare(
                spec_props[name],
                model_props[name],
                f"{path}.{name}",
                _nested_model(field.annotation) if field is not None else None,
                optional=name not in spec_required,
            )

        # Absent in the spec means "allowed" (JSON Schema default). Absent in
        # a Pydantic schema means extra="ignore": unknown keys are dropped.
        spec_extra = spec.get("additionalProperties", True)
        model_extra = model.get("additionalProperties")
        if spec_extra is True and model_extra is not True:
            verb = "rejects" if model_extra is False else "silently drops"
            self.report(
                path,
                f"spec allows additional properties but the model {verb} them (use extra='allow')",
            )
        elif spec_extra is False and model_extra is not False:
            self.report(path, "spec forbids additional properties but the model accepts them")
        elif isinstance(spec_extra, dict):
            if isinstance(model_extra, dict):
                self.compare(spec_extra, model_extra, f"{path}.*", None)
            else:
                self.report(
                    path, f"additionalProperties: spec={spec_extra!r} model={model_extra!r}"
                )


def schema_mismatches(spec: Schema, model_cls: type[BaseModel]) -> list[str]:
    """Every difference between ``spec`` and the schema ``model_cls`` generates."""
    model_schema = model_cls.model_json_schema(by_alias=True)
    diff = _SchemaDiff(spec, model_schema)
    diff.compare(spec, model_schema, "$", model_cls)
    return diff.mismatches


@cache
def _load_spec(schema_id: str) -> Schema:
    return json.loads((SPEC_DIR / f"{schema_id}.json").read_text(encoding="utf-8"))


def _load_example(schema_id: str) -> Schema:
    return json.loads((EXAMPLES_DIR / f"{schema_id}.json").read_text(encoding="utf-8"))


def test_every_spec_schema_has_a_model():
    assert SPEC_DIR.is_dir(), f"spec schemas not found at {SPEC_DIR}"
    assert sorted(p.stem for p in SPEC_DIR.glob("*.json")) == SCHEMA_IDS


def test_every_spec_schema_has_an_example():
    assert EXAMPLES_DIR.is_dir(), f"schema examples not found at {EXAMPLES_DIR}"
    assert sorted(p.stem for p in EXAMPLES_DIR.glob("*.json")) == SCHEMA_IDS


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_model_matches_spec_schema(schema_id: str):
    model_cls = SCHEMA_MODELS[schema_id]
    mismatches = schema_mismatches(_load_spec(schema_id), model_cls)
    assert not mismatches, (
        f"{model_cls.__name__} has drifted from spec/schemas/{schema_id}.json, "
        "which is the source of truth. Mismatches:\n  " + "\n  ".join(mismatches)
    )


def test_schema_diff_reports_drift():
    """Guard against a vacuous diff: a deliberately drifted model is caught."""

    class Line(BaseModel):  # extra="ignore": drops unknown keys
        amount: float = Field(ge=0)

    class Drifted(SchemaModel):
        when: str
        day: DateString | None = None
        kind: str = "x"
        lines: list[Line] = Field(default_factory=list, min_length=1)
        extra_field: int | None = None

    spec: Schema = {
        "type": "object",
        "required": ["day"],
        "properties": {
            "when": {"type": "string", "format": "date-time"},
            "day": {"type": "string", "format": "date"},
            "kind": {"type": "string", "enum": ["x", "y"]},
            "lines": {
                "type": "array",
                "items": {"type": "object", "properties": {"amount": {"type": "integer"}}},
            },
            "missing": {"type": "boolean"},
        },
    }
    found = "\n".join(schema_mismatches(spec, Drifted))
    for expected in [
        "$.day: required by the spec but optional in the model",
        "$.day: model accepts null",
        "$.when: required by the model but optional in the spec",
        "$.when: format: spec='date-time' model=None",
        "$.kind: model default 'x'",
        "$.kind: enum",
        "$.lines: model default []",
        "$.lines: minItems: spec=None model=1",
        "$.lines[].amount: type",
        "$.lines[].amount: minimum: spec=None model=0",
        "$.lines[]: spec allows additional properties but the model silently drops them",
        "$.missing: in the spec but missing from the model",
        "$.extraField: in the model but not in the spec",
    ]:
        assert expected in found, f"{expected!r} not reported in:\n{found}"


# ---------------------------------------------------------------------------
# Behavioural parity: JSON Schema validator vs model on real payloads
# ---------------------------------------------------------------------------

# jsonschema checks "date-time" only when the optional rfc3339-validator
# package is installed, so both formats get explicit RFC 3339 checkers here.
_FULL_DATE = r"(?P<year>[0-9]{4})-(?P<month>0[1-9]|1[0-2])-(?P<day>0[1-9]|[12][0-9]|3[01])"
_FULL_DATE_RE = re.compile(_FULL_DATE, re.ASCII)
_DATE_TIME_RE = re.compile(
    _FULL_DATE + r"[Tt]([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?"
    r"([Zz]|[+-]([01][0-9]|2[0-3]):[0-5][0-9])",
    re.ASCII,
)


def _day_exists(match: re.Match[str]) -> bool:
    _, days_in_month = calendar.monthrange(int(match["year"]), int(match["month"]))
    return int(match["day"]) <= days_in_month


def _is_full_date(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    match = _FULL_DATE_RE.fullmatch(instance)
    return match is not None and _day_exists(match)


def _is_date_time(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    match = _DATE_TIME_RE.fullmatch(instance)
    return match is not None and _day_exists(match)


_FORMAT_CHECKER = FormatChecker()
_FORMAT_CHECKER.checks("date")(_is_full_date)
_FORMAT_CHECKER.checks("date-time")(_is_date_time)


def _spec_errors(schema_id: str, payload: Any) -> list[str]:
    schema = _load_spec(schema_id)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema, format_checker=_FORMAT_CHECKER)
    return [
        f"{error.json_path}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda e: e.json_path)
    ]


def _assert_round_trip(schema_id: str, payload: Schema) -> None:
    errors = _spec_errors(schema_id, payload)
    assert not errors, f"payload is not valid {schema_id}:\n  " + "\n  ".join(errors)

    model = SCHEMA_MODELS[schema_id].model_validate(payload)
    dumped = model.model_dump(mode="json", by_alias=True, exclude_none=True)

    errors = _spec_errors(schema_id, dumped)
    assert not errors, f"model dump is not valid {schema_id}:\n  " + "\n  ".join(errors)
    assert dumped == payload, "round trip through the model changed the payload"


def test_format_checks_are_active():
    """The validator really rejects bad dates, or the cases below prove nothing."""
    assert _FORMAT_CHECKER.conforms("2026-03-01T09:30:00Z", "date-time")
    assert _FORMAT_CHECKER.conforms("2026-03-01T09:30:00.25-05:00", "date-time")
    assert not _FORMAT_CHECKER.conforms("2026-03-01T09:30:00", "date-time")
    assert not _FORMAT_CHECKER.conforms("2026-02-30T09:30:00Z", "date-time")
    assert _FORMAT_CHECKER.conforms("2026-03-01", "date")
    assert not _FORMAT_CHECKER.conforms("2026-02-30", "date")
    assert not _FORMAT_CHECKER.conforms("2026-03-01T00:00:00Z", "date")

    payload = _load_example("bom-v1")
    payload["metadata"]["generatedAt"] = "2026-02-28T10:30:00"
    assert _spec_errors("bom-v1", payload)


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_example_round_trips_losslessly(schema_id: str):
    _assert_round_trip(schema_id, _load_example(schema_id))


Op = tuple[Any, ...]


def _apply(payload: Schema, ops: list[Op]) -> Schema:
    """Apply ("set" | "del" | "append", "dotted.path", [value]) operations."""
    payload = copy.deepcopy(payload)
    for op, path, *value in ops:
        *parents, last = path.split(".")
        node: Any = payload
        for part in parents:
            node = node[int(part)] if isinstance(node, list) else node[part]
        key: Any = int(last) if isinstance(node, list) else last
        if op == "set":
            node[key] = value[0]
        elif op == "del":
            del node[key]
        elif op == "append":
            node[key].append(value[0])
        else:
            raise ValueError(op)
    return payload


_VENDOR_EXTENSIONS = {"acme": {"runId": "r-1842", "weights": [0.25, 0.75], "audit": {"ok": True}}}

_CREDIT_ESTIMATE_LINE = {
    "bomItemId": "LI-009",
    "description": "Deduct alternate: omit duct insulation",
    "quantity": -120,
    "unit": "LF",
    "materialUnitCost": 4.5,
    "materialTotal": -540,
    "laborHours": -6,
    "laborRate": 95,
    "laborTotal": -570,
    "equipmentCost": -25,
    "subtotal": -1135,
}

_CREDIT_QUOTE_LINE = {
    "bomItemId": "LI-002",
    "description": "Credit for returned pipe",
    "quantity": -40,
    "unit": "LF",
    "unitPrice": 17.95,
    "extendedPrice": -718,
    "manufacturer": "Sample Tube Co.",
    "partNumber": "CUL-2000-20",
    "leadTimeDays": 0,
    "availability": "in-stock",
}

VALID_MUTATIONS = [
    pytest.param(
        "estimate-v1",
        [("del", "metadata.confidence"), ("del", "metadata.pricingDate")],
        id="estimate-without-confidence-or-pricing-date",
    ),
    pytest.param(
        "estimate-v1",
        [("del", "metadata.pricingRegion"), ("del", "lineItems.0.equipmentCost")],
        id="estimate-without-pricing-region-or-equipment-cost",
    ),
    pytest.param(
        "estimate-v1",
        [("append", "lineItems", _CREDIT_ESTIMATE_LINE)],
        id="estimate-negative-credit-line",
    ),
    pytest.param("estimate-v1", [("set", "lineItems", [])], id="estimate-empty-line-items"),
    pytest.param("quote-v1", [("del", "metadata.confidence")], id="quote-without-confidence"),
    pytest.param(
        "quote-v1",
        [("append", "lineItems", _CREDIT_QUOTE_LINE), ("set", "summary.freight", -50)],
        id="quote-negative-credit-line",
    ),
    pytest.param("quote-v1", [("set", "lineItems", [])], id="quote-empty-line-items"),
    pytest.param("bom-v1", [("set", "lineItems", [])], id="bom-empty-line-items"),
    pytest.param("bom-v1", [("set", "lineItems.1.quantity", -15)], id="bom-negative-quantity"),
    pytest.param("rfi-v1", [("set", "references", [])], id="rfi-empty-references"),
    pytest.param(
        "schedule-v1",
        [("set", "activities.0.trade", "concrete")],
        id="schedule-free-text-trade",
    ),
    pytest.param(
        "schedule-v1",
        [
            ("del", "activities.0.percentComplete"),
            ("del", "activities.0.isCritical"),
            ("del", "milestones.0.isMet"),
        ],
        id="schedule-without-progress-flags",
    ),
    pytest.param(
        "change-order-v1",
        [("set", "lineItems.0.trade", "concrete")],
        id="change-order-free-text-trade",
    ),
    pytest.param(
        "change-order-v1",
        [("del", "totalScheduleImpactDays"), ("del", "lineItems.0.scheduleImpactDays")],
        id="change-order-schedule-impact-tbd",
    ),
    pytest.param(
        "change-order-v1",
        [("set", "lineItems.0.costImpact", -5000.0), ("set", "totalCostImpact", -5000.0)],
        id="change-order-credit",
    ),
    *(
        pytest.param(
            schema_id,
            [
                ("set", "metadata.vendorExtensions", _VENDOR_EXTENSIONS),
                ("set", "xAcmeTrackingId", "T-77"),
            ],
            id=f"{schema_id}-vendor-extensions",
        )
        for schema_id in SCHEMA_IDS
    ),
]


@pytest.mark.parametrize(("schema_id", "ops"), VALID_MUTATIONS)
def test_spec_valid_mutation_is_accepted_and_round_trips(schema_id: str, ops: list[Op]):
    original = _load_example(schema_id)
    payload = _apply(original, ops)
    assert payload != original
    _assert_round_trip(schema_id, payload)


_NAIVE = "2026-02-28T10:30:00"

INVALID_MUTATIONS = [
    *(
        pytest.param(schema_id, [("set", "metadata.generatedAt", _NAIVE)], id=f"{schema_id}-naive")
        for schema_id in ["bom-v1", "estimate-v1", "quote-v1", "rfi-v1"]
    ),
    pytest.param("rfi-v1", [("set", "assignedTo.role", "plumber")], id="rfi-invalid-role"),
    pytest.param("rfi-v1", [("set", "dueDate", "03/15/2026")], id="rfi-bad-due-date"),
    pytest.param(
        "estimate-v1", [("set", "metadata.pricingDate", "2026-13-01")], id="estimate-bad-date"
    ),
    pytest.param(
        "quote-v1", [("set", "validUntil", "2026-10-31T00:00:00Z")], id="quote-date-time-for-date"
    ),
    pytest.param("estimate-v1", [("set", "metadata.confidence", 1.5)], id="estimate-confidence"),
    pytest.param("estimate-v1", [("del", "metadata.generatedAt")], id="estimate-no-generated-at"),
    pytest.param("bom-v1", [("set", "trade", "concrete")], id="bom-trade-not-in-enum"),
    pytest.param("bom-v1", [("set", "lineItems.0.unit", "BOX")], id="bom-unit-not-in-enum"),
    pytest.param("schedule-v1", [("set", "activities", [])], id="schedule-no-activities"),
    pytest.param(
        "schedule-v1", [("set", "activities.0.durationDays", -1)], id="schedule-negative-duration"
    ),
    pytest.param("change-order-v1", [("set", "lineItems", [])], id="change-order-no-line-items"),
    pytest.param("change-order-v1", [("set", "title", "")], id="change-order-empty-title"),
]


@pytest.mark.parametrize(("schema_id", "ops"), INVALID_MUTATIONS)
def test_spec_invalid_mutation_is_rejected_by_both(schema_id: str, ops: list[Op]):
    payload = _apply(_load_example(schema_id), ops)
    assert _spec_errors(schema_id, payload), "the JSON Schema validator accepted the payload"
    with pytest.raises(ValidationError):
        SCHEMA_MODELS[schema_id].model_validate(payload)

"""TACO data schemas — typed construction artifact definitions.

Provides Pydantic models for TACO data schemas. Uses camelCase aliases
to match the JSON Schema files in spec/schemas/ while keeping Pythonic
snake_case internally.

The JSON Schema files are the source of truth (SPEC-003 §2.1, ADR-0002);
these models mirror them:

- A field is required here exactly when the schema lists it in
  ``required``. Optional fields default to ``None``, so
  ``model_dump(exclude_none=True)`` omits anything the producer did not
  set instead of inventing a value for it.
- Enums, numeric bounds and ``minItems``/``minLength`` constraints are
  enforced only where the schema states them.
- Unknown properties are preserved on a parse/dump round trip, because
  none of the canonical schemas forbid ``additionalProperties`` and
  SPEC-003 §4.2 recommends extending ``metadata`` (for example
  ``metadata.vendorExtensions``) rather than dropping such keys.
- Fields the schema marks ``format: date`` or ``format: date-time`` are
  stored as strings but validated against that format (see
  :data:`DateString` and :data:`DateTimeString`). Fields without a
  ``format`` in the schema are plain strings.
- ``number`` and ``integer`` fields reject strings and booleans, as JSON
  Schema does, instead of Pydantic's lax reading of ``"850"`` as 850
  (see :data:`Number` and :data:`Integer`).
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Literal

from a2a._base import A2ABaseModel
from pydantic import (
    AfterValidator,
    BeforeValidator,
    ConfigDict,
    Field,
    Strict,
    WithJsonSchema,
    model_validator,
)

from .types import (
    Availability,
    BOMUnit,
    FlagSeverity,
    RFICategory,
    RFIPriority,
    Trade,
)

# ---------------------------------------------------------------------------
# JSON Schema string formats
# ---------------------------------------------------------------------------

# RFC 3339 §5.6 full-date and date-time. "T" and "Z" may be lower case.
_FULL_DATE_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", re.ASCII)
_DATE_TIME_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
    r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.[0-9]+)?"
    r"(?:[Zz]|[+-]([0-9]{2}):([0-9]{2}))",
    re.ASCII,
)


def _coerce_date(value: object) -> object:
    if isinstance(value, _dt.datetime):
        raise ValueError(
            "expected a calendar date (YYYY-MM-DD), got a datetime; pass value.date() instead"
        )
    if isinstance(value, _dt.date):
        return value.isoformat()
    return value


def _check_date(value: str) -> str:
    match = _FULL_DATE_RE.fullmatch(value)
    try:
        if match is None:
            raise ValueError
        _dt.date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        raise ValueError(
            f"{value!r} is not a valid RFC 3339 full-date (YYYY-MM-DD)",
        ) from None
    return value


def _coerce_date_time(value: object) -> object:
    if isinstance(value, _dt.datetime):
        if value.utcoffset() is None:
            raise ValueError(
                "naive datetime: a date-time needs a timezone offset (RFC 3339); "
                "use e.g. datetime.now(timezone.utc)"
            )
        return value.isoformat()
    if isinstance(value, _dt.date):
        raise ValueError("expected a date-time with a timezone offset, got a date")
    return value


def _check_date_time(value: str) -> str:
    match = _DATE_TIME_RE.fullmatch(value)
    try:
        if match is None:
            raise ValueError
        _dt.date(int(match[1]), int(match[2]), int(match[3]))
        hour, minute, second = int(match[4]), int(match[5]), int(match[6])
        # second 60 is an RFC 3339 leap second.
        if hour > 23 or minute > 59 or second > 60:
            raise ValueError
        if match[7] is not None and (int(match[7]) > 23 or int(match[8]) > 59):
            raise ValueError
    except ValueError:
        raise ValueError(
            f"{value!r} is not a valid RFC 3339 date-time; it needs a date, a time "
            "and a timezone offset, e.g. '2026-01-01T09:30:00Z' or "
            "'2026-01-01T09:30:00-05:00'",
        ) from None
    return value


DateString = Annotated[
    str,
    BeforeValidator(_coerce_date),
    AfterValidator(_check_date),
    WithJsonSchema({"type": "string", "format": "date"}),
]
"""A JSON Schema ``format: date`` value (RFC 3339 full-date, ``YYYY-MM-DD``).

Accepts a string or a :class:`datetime.date`; always stored and serialized
as a string.
"""

DateTimeString = Annotated[
    str,
    BeforeValidator(_coerce_date_time),
    AfterValidator(_check_date_time),
    WithJsonSchema({"type": "string", "format": "date-time"}),
]
"""A JSON Schema ``format: date-time`` value (RFC 3339, offset required).

Accepts a string or a timezone-aware :class:`datetime.datetime`; always
stored and serialized as a string. Naive datetimes are rejected.
"""


# ---------------------------------------------------------------------------
# JSON Schema numbers
# ---------------------------------------------------------------------------


# Pydantic's lax mode reads "850" as 850.0 and true as 1. A JSON Schema
# number or integer is never a string or a boolean.

Number = Annotated[float, Strict()]
"""A JSON Schema ``number``: an int or a float. Rejects strings such as
``"850"`` and booleans."""


def _reject_text_and_booleans(value: object) -> object:
    if isinstance(value, bool):
        raise ValueError(f"expected a whole number, got the boolean {value!r}")
    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"expected a whole number, got the string {value!r}; send it unquoted")
    return value


# Not Strict(): strict ints reject 5.0, which JSON Schema accepts as an
# integer and which A2A's protobuf Struct produces for every number.
Integer = Annotated[int, BeforeValidator(_reject_text_and_booleans)]
"""A JSON Schema ``integer``. Accepts whole floats such as ``5.0``; rejects
``5.5``, strings such as ``"5"`` and booleans."""


class SchemaModel(A2ABaseModel):
    """Base class for models that mirror a canonical TACO JSON Schema.

    Keeps properties the model does not declare (``extra="allow"``), so
    vendor extensions survive ``model_validate`` followed by
    ``model_dump``.
    """

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# estimate-v1
# ---------------------------------------------------------------------------


class EstimateLineItem(SchemaModel):
    bom_item_id: str = Field(alias="bomItemId")
    description: str
    quantity: Number
    unit: str
    material_unit_cost: Number = Field(alias="materialUnitCost")
    material_total: Number = Field(alias="materialTotal")
    labor_hours: Number = Field(alias="laborHours")
    labor_rate: Number = Field(alias="laborRate")
    labor_total: Number = Field(alias="laborTotal")
    equipment_cost: Number | None = Field(None, alias="equipmentCost")
    subtotal: Number


class EstimateSummary(SchemaModel):
    total_material: Number = Field(alias="totalMaterial")
    total_labor: Number = Field(alias="totalLabor")
    total_equipment: Number = Field(alias="totalEquipment")
    subtotal: Number
    overhead_percentage: Number = Field(alias="overheadPercentage")
    overhead_amount: Number = Field(alias="overheadAmount")
    profit_percentage: Number = Field(alias="profitPercentage")
    profit_amount: Number = Field(alias="profitAmount")
    grand_total: Number = Field(alias="grandTotal")


class EstimateMetadata(SchemaModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: DateTimeString = Field(alias="generatedAt")
    confidence: Number | None = Field(None, ge=0.0, le=1.0)
    pricing_region: str | None = Field(None, alias="pricingRegion")
    pricing_date: DateString | None = Field(None, alias="pricingDate")
    notes: list[str] | None = None


class EstimateV1(SchemaModel):
    project_id: str = Field(alias="projectId")
    trade: Trade
    csi_division: str = Field(alias="csiDivision")
    line_items: list[EstimateLineItem] = Field(alias="lineItems")
    summary: EstimateSummary
    metadata: EstimateMetadata


# ---------------------------------------------------------------------------
# quote-v1
# ---------------------------------------------------------------------------


class QuoteLineItem(SchemaModel):
    bom_item_id: str = Field(alias="bomItemId")
    description: str
    quantity: Number
    unit: str
    unit_price: Number = Field(alias="unitPrice")
    extended_price: Number = Field(alias="extendedPrice")
    manufacturer: str
    part_number: str = Field(alias="partNumber")
    lead_time_days: Integer = Field(alias="leadTimeDays")
    availability: Availability
    notes: str | None = None


class QuoteSummary(SchemaModel):
    subtotal: Number
    tax_rate: Number = Field(alias="taxRate")
    tax_amount: Number = Field(alias="taxAmount")
    freight: Number
    total: Number


class QuoteTerms(SchemaModel):
    payment_terms: str = Field(alias="paymentTerms")
    delivery_method: str = Field(alias="deliveryMethod")
    warranty: str
    return_policy: str = Field(alias="returnPolicy")


class QuoteMetadata(SchemaModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: DateTimeString = Field(alias="generatedAt")
    confidence: Number | None = Field(None, ge=0.0, le=1.0)


class QuoteV1(SchemaModel):
    project_id: str = Field(alias="projectId")
    supplier_name: str = Field(alias="supplierName")
    quote_number: str = Field(alias="quoteNumber")
    valid_until: DateString = Field(alias="validUntil")
    line_items: list[QuoteLineItem] = Field(alias="lineItems")
    summary: QuoteSummary
    terms: QuoteTerms
    metadata: QuoteMetadata


# ---------------------------------------------------------------------------
# bom-v1
# ---------------------------------------------------------------------------


class BOMAlternate(SchemaModel):
    description: str | None = None
    manufacturer: str | None = None
    part_number: str | None = Field(None, alias="partNumber")


class BOMLineItem(SchemaModel):
    id: str
    description: str
    quantity: Number
    unit: BOMUnit
    size: str | None = None
    material: str | None = None
    spec_section: str | None = Field(None, alias="specSection")
    source_sheet: str | None = Field(None, alias="sourceSheet")
    location: str | None = None
    alternates: list[BOMAlternate] | None = None


class BOMSourceDocument(SchemaModel):
    filename: str | None = None
    sheet_id: str | None = Field(None, alias="sheetId")
    revision: str | None = None


class BOMFlaggedItem(SchemaModel):
    line_item_id: str | None = Field(None, alias="lineItemId")
    reason: str | None = None
    severity: FlagSeverity | None = None


class BOMMetadata(SchemaModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: DateTimeString = Field(alias="generatedAt")
    confidence: Number | None = Field(None, ge=0.0, le=1.0)
    source_documents: list[BOMSourceDocument] | None = Field(None, alias="sourceDocuments")
    flagged_items: list[BOMFlaggedItem] | None = Field(None, alias="flaggedItems")


class BOMV1(SchemaModel):
    project_id: str = Field(alias="projectId")
    revision: str | None = None
    trade: Trade
    csi_division: str = Field(alias="csiDivision")
    line_items: list[BOMLineItem] = Field(alias="lineItems")
    metadata: BOMMetadata


# ---------------------------------------------------------------------------
# rfi-v1
# ---------------------------------------------------------------------------


class RFICoordinates(SchemaModel):
    x: Number
    y: Number
    width: Number
    height: Number


class RFIReference(SchemaModel):
    sheet_id: str = Field(alias="sheetId")
    area: str | None = None
    coordinates: RFICoordinates | None = None
    markup: str | None = None


RFIAssigneeRole = Literal[
    "architect",
    "engineer",
    "owner",
    "contractor",
    "subcontractor",
]


class RFIAssignee(SchemaModel):
    role: RFIAssigneeRole | None = None
    company: str | None = None
    contact: str | None = None


class RFIMetadata(SchemaModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: DateTimeString = Field(alias="generatedAt")
    confidence: Number | None = Field(None, ge=0.0, le=1.0)
    related_rfis: list[str] | None = Field(None, alias="relatedRfis")


class RFIV1(SchemaModel):
    project_id: str = Field(alias="projectId")
    subject: str
    question: str
    category: RFICategory
    priority: RFIPriority
    references: list[RFIReference]
    suggested_resolution: str | None = Field(None, alias="suggestedResolution")
    related_bom_items: list[str] | None = Field(None, alias="relatedBomItems")
    due_date: DateString | None = Field(None, alias="dueDate")
    assigned_to: RFIAssignee | None = Field(None, alias="assignedTo")
    metadata: RFIMetadata


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

BOMSchema = BOMV1
RFISchema = RFIV1


# ---------------------------------------------------------------------------
# schedule-v1
# ---------------------------------------------------------------------------


class ScheduleActivity(SchemaModel):
    id: str = Field(min_length=1)
    name: str
    # Free text in schedule-v1 (unlike the Trade enum on bom/estimate).
    trade: str | None = None
    duration_days: Integer = Field(ge=0, alias="durationDays")
    # schedule-v1 dates declare no ``format``, so any string is accepted.
    start_date: str | None = Field(None, alias="startDate")
    end_date: str | None = Field(None, alias="endDate")
    predecessors: list[str] | None = None
    successors: list[str] | None = None
    percent_complete: Number | None = Field(None, ge=0.0, le=100.0, alias="percentComplete")
    is_critical: bool | None = Field(None, alias="isCritical")
    resources: list[str] | None = None


class ScheduleMilestone(SchemaModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    date: str
    is_met: bool | None = Field(None, alias="isMet")


class ScheduleMetadata(SchemaModel):
    generated_by: str = Field(alias="generatedBy")
    # schedule-v1 declares no ``format`` here (unlike bom/estimate/quote/rfi).
    generated_at: str = Field(alias="generatedAt")
    confidence: Number | None = Field(None, ge=0.0, le=1.0)
    notes: list[str] | None = None


class ScheduleV1(SchemaModel):
    project_id: str = Field(alias="projectId")
    start_date: str | None = Field(None, alias="startDate")
    end_date: str | None = Field(None, alias="endDate")
    activities: list[ScheduleActivity] = Field(min_length=1)
    milestones: list[ScheduleMilestone] | None = None
    metadata: ScheduleMetadata

    @model_validator(mode="after")
    def _check_unique_activity_ids(self) -> ScheduleV1:
        # schedule-v1 states "IDs must be unique" in the description of
        # ``activities``; JSON Schema cannot express that, so it is checked here.
        ids = [a.id for a in self.activities]
        if len(set(ids)) != len(ids):
            dupes = sorted({x for x in ids if ids.count(x) > 1})
            raise ValueError(f"Duplicate activity IDs: {dupes}")
        return self


ScheduleSchema = ScheduleV1


# ---------------------------------------------------------------------------
# change-order-v1
# ---------------------------------------------------------------------------

ChangeOrderStatus = Literal[
    "draft",
    "submitted",
    "approved",
    "rejected",
    "withdrawn",
]

ChangeOrderReason = Literal[
    "design-change",
    "unforeseen-condition",
    "owner-request",
    "value-engineering",
    "code-compliance",
    "error-omission",
]


class ChangeOrderLineItem(SchemaModel):
    id: str = Field(min_length=1)
    description: str
    # Free text in change-order-v1 (unlike the Trade enum on bom/estimate).
    trade: str | None = None
    cost_impact: Number = Field(alias="costImpact")
    schedule_impact_days: Integer | None = Field(None, alias="scheduleImpactDays")
    bom_item_ids: list[str] | None = Field(None, alias="bomItemIds")


class ChangeOrderMetadata(SchemaModel):
    generated_by: str = Field(alias="generatedBy")
    # change-order-v1 declares no ``format`` here (unlike bom/estimate/quote/rfi).
    generated_at: str = Field(alias="generatedAt")
    confidence: Number | None = Field(None, ge=0.0, le=1.0)
    notes: list[str] | None = None


class ChangeOrderV1(SchemaModel):
    project_id: str = Field(alias="projectId")
    change_order_number: str = Field(alias="changeOrderNumber", min_length=1)
    title: str = Field(min_length=1)
    reason: ChangeOrderReason
    status: ChangeOrderStatus
    line_items: list[ChangeOrderLineItem] = Field(alias="lineItems", min_length=1)
    total_cost_impact: Number = Field(alias="totalCostImpact")
    total_schedule_impact_days: Integer | None = Field(None, alias="totalScheduleImpactDays")
    related_rfis: list[str] | None = Field(None, alias="relatedRfis")
    metadata: ChangeOrderMetadata


ChangeOrderSchema = ChangeOrderV1


# ---------------------------------------------------------------------------
# Schema registry
# ---------------------------------------------------------------------------

SCHEMA_MODELS: Mapping[str, type[SchemaModel]] = MappingProxyType(
    {
        "bom-v1": BOMV1,
        "change-order-v1": ChangeOrderV1,
        "estimate-v1": EstimateV1,
        "quote-v1": QuoteV1,
        "rfi-v1": RFIV1,
        "schedule-v1": ScheduleV1,
    }
)
"""Read-only map from canonical schema name (SPEC-003 §3.1) to its model."""


def get_schema_model(schema_id: str) -> type[SchemaModel]:
    """Return the model for a canonical schema name such as ``"bom-v1"``.

    ``schema_id`` is the bare name used in ``inputSchema`` / ``outputSchema``
    (SPEC-003 §3.2). Raises :class:`KeyError` naming the known ids when it is
    not a canonical TACO schema.
    """
    try:
        return SCHEMA_MODELS[schema_id]
    except KeyError:
        known = ", ".join(sorted(SCHEMA_MODELS))
        raise KeyError(f"Unknown TACO schema id {schema_id!r}; known ids: {known}") from None

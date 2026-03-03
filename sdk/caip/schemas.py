"""CAIP data schemas — typed construction artifact definitions.

Provides Pydantic models for CAIP data schemas. Uses camelCase aliases
to match the JSON Schema files in spec/schemas/ while keeping Pythonic
snake_case internally.
"""

from __future__ import annotations

from pydantic import Field

from .models import (
    Availability,
    BOMUnit,
    CaipBaseModel,
    FlagSeverity,
    RFICategory,
    RFIPriority,
    Trade,
)


# ---------------------------------------------------------------------------
# estimate-v1
# ---------------------------------------------------------------------------

class EstimateLineItem(CaipBaseModel):
    bom_item_id: str = Field(alias="bomItemId")
    description: str
    quantity: float = Field(ge=0)
    unit: str
    material_unit_cost: float = Field(ge=0, alias="materialUnitCost")
    material_total: float = Field(ge=0, alias="materialTotal")
    labor_hours: float = Field(ge=0, alias="laborHours")
    labor_rate: float = Field(ge=0, alias="laborRate")
    labor_total: float = Field(ge=0, alias="laborTotal")
    equipment_cost: float = Field(0.0, ge=0, alias="equipmentCost")
    subtotal: float = Field(ge=0)


class EstimateSummary(CaipBaseModel):
    total_material: float = Field(ge=0, alias="totalMaterial")
    total_labor: float = Field(ge=0, alias="totalLabor")
    total_equipment: float = Field(ge=0, alias="totalEquipment")
    subtotal: float = Field(ge=0)
    overhead_percentage: float = Field(ge=0, alias="overheadPercentage")
    overhead_amount: float = Field(ge=0, alias="overheadAmount")
    profit_percentage: float = Field(ge=0, alias="profitPercentage")
    profit_amount: float = Field(ge=0, alias="profitAmount")
    grand_total: float = Field(ge=0, alias="grandTotal")


class EstimateMetadata(CaipBaseModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: str = Field(alias="generatedAt")
    confidence: float = Field(ge=0.0, le=1.0)
    pricing_region: str = Field("US-National", alias="pricingRegion")
    pricing_date: str = Field(alias="pricingDate")
    notes: list[str] = Field(default_factory=list)


class EstimateV1(CaipBaseModel):
    project_id: str = Field(alias="projectId")
    trade: Trade
    csi_division: str = Field(alias="csiDivision")
    line_items: list[EstimateLineItem] = Field(alias="lineItems", min_length=1)
    summary: EstimateSummary
    metadata: EstimateMetadata


# ---------------------------------------------------------------------------
# quote-v1
# ---------------------------------------------------------------------------

class QuoteLineItem(CaipBaseModel):
    bom_item_id: str = Field(alias="bomItemId")
    description: str
    quantity: float = Field(ge=0)
    unit: str
    unit_price: float = Field(ge=0, alias="unitPrice")
    extended_price: float = Field(ge=0, alias="extendedPrice")
    manufacturer: str
    part_number: str = Field(alias="partNumber")
    lead_time_days: int = Field(ge=0, alias="leadTimeDays")
    availability: Availability
    notes: str | None = None


class QuoteSummary(CaipBaseModel):
    subtotal: float = Field(ge=0)
    tax_rate: float = Field(ge=0, alias="taxRate")
    tax_amount: float = Field(ge=0, alias="taxAmount")
    freight: float = Field(ge=0)
    total: float = Field(ge=0)


class QuoteTerms(CaipBaseModel):
    payment_terms: str = Field(alias="paymentTerms")
    delivery_method: str = Field(alias="deliveryMethod")
    warranty: str
    return_policy: str = Field(alias="returnPolicy")


class QuoteMetadata(CaipBaseModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: str = Field(alias="generatedAt")
    confidence: float = Field(ge=0.0, le=1.0)


class QuoteV1(CaipBaseModel):
    project_id: str = Field(alias="projectId")
    supplier_name: str = Field(alias="supplierName")
    quote_number: str = Field(alias="quoteNumber")
    valid_until: str = Field(alias="validUntil")
    line_items: list[QuoteLineItem] = Field(alias="lineItems", min_length=1)
    summary: QuoteSummary
    terms: QuoteTerms
    metadata: QuoteMetadata


# ---------------------------------------------------------------------------
# bom-v1
# ---------------------------------------------------------------------------

class BOMAlternate(CaipBaseModel):
    description: str | None = None
    manufacturer: str | None = None
    part_number: str | None = Field(None, alias="partNumber")


class BOMLineItem(CaipBaseModel):
    id: str
    description: str
    quantity: float = Field(ge=0)
    unit: BOMUnit
    size: str | None = None
    material: str | None = None
    spec_section: str | None = Field(None, alias="specSection")
    source_sheet: str | None = Field(None, alias="sourceSheet")
    location: str | None = None
    alternates: list[BOMAlternate] = Field(default_factory=list)


class BOMSourceDocument(CaipBaseModel):
    filename: str | None = None
    sheet_id: str | None = Field(None, alias="sheetId")
    revision: str | None = None


class BOMFlaggedItem(CaipBaseModel):
    line_item_id: str | None = Field(None, alias="lineItemId")
    reason: str | None = None
    severity: FlagSeverity | None = None


class BOMMetadata(CaipBaseModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: str = Field(alias="generatedAt")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_documents: list[BOMSourceDocument] = Field(
        default_factory=list, alias="sourceDocuments",
    )
    flagged_items: list[BOMFlaggedItem] = Field(
        default_factory=list, alias="flaggedItems",
    )


class BOMV1(CaipBaseModel):
    project_id: str = Field(alias="projectId")
    revision: str | None = None
    trade: Trade
    csi_division: str = Field(alias="csiDivision")
    line_items: list[BOMLineItem] = Field(alias="lineItems", min_length=1)
    metadata: BOMMetadata


# ---------------------------------------------------------------------------
# rfi-v1
# ---------------------------------------------------------------------------

class RFICoordinates(CaipBaseModel):
    x: float
    y: float
    width: float
    height: float


class RFIReference(CaipBaseModel):
    sheet_id: str = Field(alias="sheetId")
    area: str | None = None
    coordinates: RFICoordinates | None = None
    markup: str | None = None


class RFIAssignee(CaipBaseModel):
    role: str | None = None
    company: str | None = None
    contact: str | None = None


class RFIMetadata(CaipBaseModel):
    generated_by: str = Field(alias="generatedBy")
    generated_at: str = Field(alias="generatedAt")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    related_rfis: list[str] = Field(default_factory=list, alias="relatedRfis")


class RFIV1(CaipBaseModel):
    project_id: str = Field(alias="projectId")
    subject: str
    question: str
    category: RFICategory
    priority: RFIPriority
    references: list[RFIReference] = Field(min_length=1)
    suggested_resolution: str | None = Field(None, alias="suggestedResolution")
    related_bom_items: list[str] = Field(
        default_factory=list, alias="relatedBomItems",
    )
    due_date: str | None = Field(None, alias="dueDate")
    assigned_to: RFIAssignee | None = Field(None, alias="assignedTo")
    metadata: RFIMetadata


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

BOMSchema = BOMV1
RFISchema = RFIV1


# ---------------------------------------------------------------------------
# Stubs — schemas defined in spec but not yet implemented as Pydantic models.
# These raise NotImplementedError to prevent silent data loss.
# ---------------------------------------------------------------------------

class _StubSchema(CaipBaseModel):
    """Base for unimplemented schemas that fail loudly."""

    schema_id: str

    def __init__(self, **data: object) -> None:
        if set(data.keys()) - {"schema_id"}:
            raise NotImplementedError(
                f"{type(self).__name__} is not yet implemented. "
                f"See spec/schemas/{self.model_fields['schema_id'].default}.schema.json "
                f"for the expected format."
            )
        super().__init__(**data)


class ScheduleSchema(_StubSchema):
    schema_id: str = "schedule-v1"


class ChangeOrderSchema(_StubSchema):
    schema_id: str = "change-order-v1"

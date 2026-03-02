"""CAIP data schemas — typed construction artifact definitions.

Provides Pydantic models for CAIP data schemas. Uses camelCase aliases
to match the JSON Schema files in spec/schemas/ while keeping Pythonic
snake_case internally.
"""

from __future__ import annotations

from pydantic import Field

from .models import Availability, CaipBaseModel, Trade


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


class BOMSchema(_StubSchema):
    schema_id: str = "bom-v1"


class RFISchema(_StubSchema):
    schema_id: str = "rfi-v1"


class ScheduleSchema(_StubSchema):
    schema_id: str = "schedule-v1"


class ChangeOrderSchema(_StubSchema):
    schema_id: str = "change-order-v1"

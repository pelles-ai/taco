"""Tests for taco.schemas — TACO data schema models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from taco.schemas import (
    BOMAlternate,
    BOMFlaggedItem,
    BOMLineItem,
    BOMMetadata,
    BOMSchema,
    BOMSourceDocument,
    BOMV1,
    EstimateLineItem,
    EstimateMetadata,
    EstimateSummary,
    EstimateV1,
    QuoteLineItem,
    QuoteMetadata,
    QuoteSummary,
    QuoteTerms,
    QuoteV1,
    RFIAssignee,
    RFICoordinates,
    RFIMetadata,
    RFIReference,
    RFISchema,
    RFIV1,
)


class TestEstimateV1:
    def test_valid_estimate(self):
        est = EstimateV1(
            project_id="PRJ-001",
            trade="mechanical",
            csi_division="23",
            line_items=[
                EstimateLineItem(
                    bom_item_id="LI-001",
                    description="Test item",
                    quantity=10.0,
                    unit="EA",
                    material_unit_cost=100.0,
                    material_total=1000.0,
                    labor_hours=8.0,
                    labor_rate=95.0,
                    labor_total=760.0,
                    subtotal=1760.0,
                ),
            ],
            summary=EstimateSummary(
                total_material=1000.0,
                total_labor=760.0,
                total_equipment=0.0,
                subtotal=1760.0,
                overhead_percentage=0.12,
                overhead_amount=211.2,
                profit_percentage=0.10,
                profit_amount=197.12,
                grand_total=2168.32,
            ),
            metadata=EstimateMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=0.85,
                pricing_date="2026-01-01",
            ),
        )
        # A2ABaseModel serializes by alias by default
        data = est.model_dump()
        assert data["projectId"] == "PRJ-001"
        assert len(data["lineItems"]) == 1

    def test_negative_quantity_fails(self):
        with pytest.raises(ValidationError):
            EstimateLineItem(
                bom_item_id="LI-001",
                description="Test",
                quantity=-5.0,
                unit="EA",
                material_unit_cost=100.0,
                material_total=1000.0,
                labor_hours=8.0,
                labor_rate=95.0,
                labor_total=760.0,
                subtotal=1760.0,
            )

    def test_confidence_above_1_fails(self):
        with pytest.raises(ValidationError):
            EstimateMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=1.5,
                pricing_date="2026-01-01",
            )

    def test_confidence_below_0_fails(self):
        with pytest.raises(ValidationError):
            EstimateMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=-0.1,
                pricing_date="2026-01-01",
            )


class TestQuoteV1:
    def test_valid_quote(self):
        quote = QuoteV1(
            project_id="PRJ-001",
            supplier_name="ACME Supply",
            quote_number="Q-2026-001",
            valid_until="2026-03-01",
            line_items=[
                QuoteLineItem(
                    bom_item_id="LI-001",
                    description="Copper pipe 4in",
                    quantity=100.0,
                    unit="LF",
                    unit_price=45.0,
                    extended_price=4500.0,
                    manufacturer="Mueller",
                    part_number="MU-4L",
                    lead_time_days=14,
                    availability="in-stock",
                ),
            ],
            summary=QuoteSummary(
                subtotal=4500.0,
                tax_rate=0.08,
                tax_amount=360.0,
                freight=250.0,
                total=5110.0,
            ),
            terms=QuoteTerms(
                payment_terms="Net 30",
                delivery_method="FOB jobsite",
                warranty="1 year",
                return_policy="30-day return",
            ),
            metadata=QuoteMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=0.92,
            ),
        )
        data = quote.model_dump()
        assert data["supplierName"] == "ACME Supply"
        assert data["lineItems"][0]["leadTimeDays"] == 14


class TestBOMV1:
    def test_valid_bom(self, sample_bom: dict):
        bom = BOMV1.model_validate(sample_bom)
        assert bom.project_id == "PRJ-TEST-001"
        assert bom.trade == "mechanical"
        assert len(bom.line_items) == 2
        assert bom.line_items[0].unit == "EA"

    def test_bom_round_trip(self, sample_bom: dict):
        bom = BOMV1.model_validate(sample_bom)
        data = bom.model_dump(exclude_none=True)
        bom2 = BOMV1.model_validate(data)
        assert bom2.project_id == bom.project_id
        assert len(bom2.line_items) == len(bom.line_items)

    def test_bom_with_alternates(self):
        bom = BOMV1(
            project_id="PRJ-002",
            trade="electrical",
            csi_division="26",
            line_items=[
                BOMLineItem(
                    id="LI-001",
                    description="Panel board",
                    quantity=1,
                    unit="EA",
                    alternates=[
                        BOMAlternate(
                            description="Eaton panel",
                            manufacturer="Eaton",
                            part_number="EP-100",
                        ),
                    ],
                ),
            ],
            metadata=BOMMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
            ),
        )
        assert len(bom.line_items[0].alternates) == 1

    def test_bom_with_source_docs_and_flags(self):
        bom = BOMV1(
            project_id="PRJ-003",
            trade="plumbing",
            csi_division="22",
            line_items=[
                BOMLineItem(id="LI-001", description="Pipe", quantity=100, unit="LF"),
            ],
            metadata=BOMMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=0.8,
                source_documents=[
                    BOMSourceDocument(filename="plans.pdf", sheet_id="P-101", revision="A"),
                ],
                flagged_items=[
                    BOMFlaggedItem(
                        line_item_id="LI-001",
                        reason="Verify size",
                        severity="warning",
                    ),
                ],
            ),
        )
        assert len(bom.metadata.source_documents) == 1
        assert bom.metadata.flagged_items[0].severity == "warning"

    def test_bom_empty_line_items_fails(self):
        with pytest.raises(ValidationError):
            BOMV1(
                project_id="PRJ-004",
                trade="mechanical",
                csi_division="23",
                line_items=[],
                metadata=BOMMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_bom_schema_alias(self):
        """BOMSchema should be the same class as BOMV1."""
        assert BOMSchema is BOMV1

    def test_sample_data_validates(self):
        full_bom = {
            "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
            "revision": "Rev C",
            "trade": "mechanical",
            "csiDivision": "23",
            "lineItems": [
                {
                    "id": "LI-001",
                    "description": "Rooftop Unit, 25-ton",
                    "quantity": 2,
                    "unit": "EA",
                    "alternates": [
                        {"description": "Carrier 48HC", "manufacturer": "Carrier", "partNumber": "48HC-A28"},
                    ],
                },
            ],
            "metadata": {
                "generatedBy": "manual-entry",
                "generatedAt": "2026-02-28T10:30:00Z",
                "confidence": 0.95,
                "sourceDocuments": [
                    {"filename": "test.pdf", "sheetId": "M-101", "revision": "C"},
                ],
                "flaggedItems": [
                    {"lineItemId": "LI-001", "reason": "Verify size", "severity": "info"},
                ],
            },
        }
        bom = BOMV1.model_validate(full_bom)
        assert bom.revision == "Rev C"


class TestRFIV1:
    def test_valid_rfi(self):
        rfi = RFIV1(
            project_id="PRJ-001",
            subject="Pipe size discrepancy",
            question="Drawing M-201 shows 4-inch but schedule says 3-inch. Which is correct?",
            category="design-conflict",
            priority="high",
            references=[
                RFIReference(
                    sheet_id="M-201",
                    area="grid D4-E6",
                    coordinates=RFICoordinates(x=100, y=200, width=50, height=30),
                ),
            ],
            suggested_resolution="Use 4-inch as shown on plan",
            related_bom_items=["LI-006"],
            metadata=RFIMetadata(
                generated_by="test-agent",
                generated_at="2026-01-01T00:00:00Z",
                confidence=0.85,
            ),
        )
        data = rfi.model_dump(exclude_none=True)
        assert data["category"] == "design-conflict"
        assert data["priority"] == "high"
        assert data["references"][0]["sheetId"] == "M-201"
        assert data["suggestedResolution"] == "Use 4-inch as shown on plan"

    def test_rfi_round_trip(self):
        rfi_data = {
            "projectId": "PRJ-001",
            "subject": "Missing info",
            "question": "What is the spec for insulation?",
            "category": "missing-information",
            "priority": "medium",
            "references": [{"sheetId": "M-401"}],
            "metadata": {
                "generatedBy": "test",
                "generatedAt": "2026-01-01T00:00:00Z",
            },
        }
        rfi = RFIV1.model_validate(rfi_data)
        data = rfi.model_dump(exclude_none=True)
        rfi2 = RFIV1.model_validate(data)
        assert rfi2.subject == rfi.subject
        assert rfi2.category == rfi.category

    def test_rfi_with_assignee(self):
        rfi = RFIV1(
            project_id="PRJ-001",
            subject="Coordination issue",
            question="HVAC duct conflicts with structural beam",
            category="coordination",
            priority="critical",
            references=[RFIReference(sheet_id="S-301")],
            assigned_to=RFIAssignee(
                role="engineer",
                company="Smith Engineering",
                contact="john@smith.com",
            ),
            metadata=RFIMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
            ),
        )
        data = rfi.model_dump(exclude_none=True)
        assert data["assignedTo"]["role"] == "engineer"

    def test_rfi_empty_references_fails(self):
        with pytest.raises(ValidationError):
            RFIV1(
                project_id="PRJ-001",
                subject="Test",
                question="Test?",
                category="clarification",
                priority="low",
                references=[],
                metadata=RFIMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_rfi_schema_alias(self):
        """RFISchema should be the same class as RFIV1."""
        assert RFISchema is RFIV1

    def test_rfi_invalid_category_fails(self):
        with pytest.raises(ValidationError):
            RFIV1(
                project_id="PRJ-001",
                subject="Test",
                question="Test?",
                category="nonexistent",
                priority="low",
                references=[RFIReference(sheet_id="M-101")],
                metadata=RFIMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_rfi_invalid_priority_fails(self):
        with pytest.raises(ValidationError):
            RFIV1(
                project_id="PRJ-001",
                subject="Test",
                question="Test?",
                category="clarification",
                priority="nonexistent",
                references=[RFIReference(sheet_id="M-101")],
                metadata=RFIMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

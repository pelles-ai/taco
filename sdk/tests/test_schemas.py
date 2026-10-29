"""Tests for taco.schemas — TACO data schema models."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from taco.schemas import (
    BOMV1,
    RFIV1,
    BOMAlternate,
    BOMFlaggedItem,
    BOMLineItem,
    BOMMetadata,
    BOMSchema,
    BOMSourceDocument,
    ChangeOrderLineItem,
    ChangeOrderMetadata,
    ChangeOrderSchema,
    ChangeOrderV1,
    DateString,
    DateTimeString,
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
    ScheduleActivity,
    ScheduleMetadata,
    ScheduleMilestone,
    ScheduleSchema,
    ScheduleV1,
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

    def test_negative_credit_line_is_valid(self):
        """estimate-v1 sets no minimum on amounts: credit lines are negative."""
        item = EstimateLineItem(
            bom_item_id="LI-001",
            description="Deduct alternate: omit insulation",
            quantity=-5.0,
            unit="EA",
            material_unit_cost=100.0,
            material_total=-500.0,
            labor_hours=-2.0,
            labor_rate=95.0,
            labor_total=-190.0,
            equipment_cost=-50.0,
            subtotal=-740.0,
        )
        assert item.subtotal == -740.0

    def test_negative_summary_is_valid(self):
        summary = EstimateSummary(
            total_material=-500.0,
            total_labor=-190.0,
            total_equipment=0.0,
            subtotal=-690.0,
            overhead_percentage=0.0,
            overhead_amount=0.0,
            profit_percentage=0.0,
            profit_amount=0.0,
            grand_total=-690.0,
        )
        assert summary.grand_total == -690.0

    def test_metadata_requires_only_generated_by_and_at(self):
        meta = EstimateMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z")
        assert meta.confidence is None
        assert meta.pricing_date is None
        assert meta.pricing_region is None
        assert meta.notes is None
        assert meta.model_dump(exclude_none=True) == {
            "generatedBy": "test",
            "generatedAt": "2026-01-01T00:00:00Z",
        }

    def test_optional_equipment_cost_is_omitted(self):
        item = EstimateLineItem(
            bom_item_id="LI-001",
            description="Test",
            quantity=1,
            unit="EA",
            material_unit_cost=1.0,
            material_total=1.0,
            labor_hours=0.0,
            labor_rate=0.0,
            labor_total=0.0,
            subtotal=1.0,
        )
        assert item.equipment_cost is None
        assert "equipmentCost" not in item.model_dump(exclude_none=True)

    def test_empty_line_items_is_valid(self):
        est = EstimateV1.model_validate(
            {
                "projectId": "PRJ-001",
                "trade": "general",
                "csiDivision": "01",
                "lineItems": [],
                "summary": {
                    "totalMaterial": 0,
                    "totalLabor": 0,
                    "totalEquipment": 0,
                    "subtotal": 0,
                    "overheadPercentage": 0,
                    "overheadAmount": 0,
                    "profitPercentage": 0,
                    "profitAmount": 0,
                    "grandTotal": 0,
                },
                "metadata": {"generatedBy": "test", "generatedAt": "2026-01-01T00:00:00Z"},
            }
        )
        assert est.line_items == []

    def test_invalid_trade_fails(self):
        """estimate-v1 keeps trade as an enum."""
        with pytest.raises(ValidationError):
            EstimateV1.model_validate(
                {
                    "projectId": "PRJ-001",
                    "trade": "concrete",
                    "csiDivision": "03",
                    "lineItems": [],
                    "summary": {
                        "totalMaterial": 0,
                        "totalLabor": 0,
                        "totalEquipment": 0,
                        "subtotal": 0,
                        "overheadPercentage": 0,
                        "overheadAmount": 0,
                        "profitPercentage": 0,
                        "profitAmount": 0,
                        "grandTotal": 0,
                    },
                    "metadata": {"generatedBy": "test", "generatedAt": "2026-01-01T00:00:00Z"},
                }
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

    def test_metadata_confidence_is_optional(self):
        meta = QuoteMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z")
        assert meta.confidence is None
        assert "confidence" not in meta.model_dump(exclude_none=True)

    def test_credit_line_and_negative_summary_are_valid(self):
        """quote-v1 sets no minimum on amounts: credits are negative."""
        item = QuoteLineItem(
            bom_item_id="LI-001",
            description="Restocking credit",
            quantity=-10.0,
            unit="LF",
            unit_price=45.0,
            extended_price=-450.0,
            manufacturer="Mueller",
            part_number="MU-4L",
            lead_time_days=0,
            availability="in-stock",
        )
        summary = QuoteSummary(
            subtotal=-450.0,
            tax_rate=0.08,
            tax_amount=-36.0,
            freight=0.0,
            total=-486.0,
        )
        assert item.extended_price == -450.0
        assert summary.total == -486.0

    def test_empty_line_items_is_valid(self):
        """quote-v1 sets no minItems on lineItems."""
        quote = QuoteV1(
            project_id="PRJ-001",
            supplier_name="ACME Supply",
            quote_number="Q-0",
            valid_until="2026-03-01",
            line_items=[],
            summary=QuoteSummary(subtotal=0, tax_rate=0, tax_amount=0, freight=0, total=0),
            terms=QuoteTerms(
                payment_terms="Net 30",
                delivery_method="Pickup",
                warranty="None",
                return_policy="None",
            ),
            metadata=QuoteMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z"),
        )
        assert quote.line_items == []


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

    def test_bom_empty_line_items_is_valid(self):
        """bom-v1 sets no minItems on lineItems."""
        bom = BOMV1(
            project_id="PRJ-004",
            trade="mechanical",
            csi_division="23",
            line_items=[],
            metadata=BOMMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
            ),
        )
        assert bom.line_items == []

    def test_bom_negative_quantity_is_valid(self):
        """bom-v1 sets no minimum on quantity."""
        item = BOMLineItem(id="LI-001", description="Removed pipe", quantity=-10, unit="LF")
        assert item.quantity == -10

    def test_bom_unset_lists_are_omitted(self):
        bom = BOMV1(
            project_id="PRJ-005",
            trade="plumbing",
            csi_division="22",
            line_items=[BOMLineItem(id="LI-001", description="Pipe", quantity=1, unit="LF")],
            metadata=BOMMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z"),
        )
        data = bom.model_dump(exclude_none=True)
        assert "alternates" not in data["lineItems"][0]
        assert "sourceDocuments" not in data["metadata"]
        assert "flaggedItems" not in data["metadata"]

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
                        {
                            "description": "Carrier 48HC",
                            "manufacturer": "Carrier",
                            "partNumber": "48HC-A28",
                        },
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

    def test_rfi_empty_references_is_valid(self):
        """rfi-v1 requires references but sets no minItems."""
        rfi = RFIV1(
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
        assert rfi.references == []

    def test_rfi_missing_references_fails(self):
        with pytest.raises(ValidationError):
            RFIV1.model_validate(
                {
                    "projectId": "PRJ-001",
                    "subject": "Test",
                    "question": "Test?",
                    "category": "clarification",
                    "priority": "low",
                    "metadata": {"generatedBy": "test", "generatedAt": "2026-01-01T00:00:00Z"},
                }
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


class TestScheduleV1:
    def test_valid_schedule(self):
        sched = ScheduleV1(
            project_id="PRJ-001",
            start_date="2026-03-01",
            end_date="2026-09-30",
            activities=[
                ScheduleActivity(
                    id="ACT-001",
                    name="Foundation pour",
                    trade="structural",
                    duration_days=5,
                    start_date="2026-03-01",
                    end_date="2026-03-06",
                    percent_complete=100.0,
                    is_critical=True,
                ),
            ],
            milestones=[
                ScheduleMilestone(
                    id="MS-001",
                    name="Foundation complete",
                    date="2026-03-06",
                    is_met=True,
                ),
            ],
            metadata=ScheduleMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=0.9,
            ),
        )
        data = sched.model_dump(exclude_none=True)
        assert data["projectId"] == "PRJ-001"
        assert len(data["activities"]) == 1
        assert data["activities"][0]["durationDays"] == 5
        assert data["activities"][0]["isCritical"] is True
        assert data["milestones"][0]["isMet"] is True

    def test_schedule_round_trip(self):
        sched_data = {
            "projectId": "PRJ-002",
            "activities": [
                {
                    "id": "ACT-001",
                    "name": "Excavation",
                    "durationDays": 10,
                    "percentComplete": 50.0,
                },
            ],
            "metadata": {
                "generatedBy": "scheduler",
                "generatedAt": "2026-02-01T00:00:00Z",
            },
        }
        sched = ScheduleV1.model_validate(sched_data)
        data = sched.model_dump(exclude_none=True)
        sched2 = ScheduleV1.model_validate(data)
        assert sched2.project_id == sched.project_id
        assert sched2.activities[0].percent_complete == 50.0

    def test_schedule_empty_activities_fails(self):
        with pytest.raises(ValidationError):
            ScheduleV1(
                project_id="PRJ-003",
                activities=[],
                metadata=ScheduleMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_schedule_negative_duration_fails(self):
        with pytest.raises(ValidationError):
            ScheduleActivity(
                id="ACT-001",
                name="Bad activity",
                duration_days=-5,
            )

    def test_schedule_percent_complete_bounds(self):
        with pytest.raises(ValidationError):
            ScheduleActivity(
                id="ACT-001",
                name="Over 100",
                duration_days=5,
                percent_complete=101.0,
            )

    def test_schedule_schema_alias(self):
        assert ScheduleSchema is ScheduleV1

    def test_schedule_empty_activity_id_fails(self):
        with pytest.raises(ValidationError):
            ScheduleActivity(
                id="",
                name="Bad activity",
                duration_days=5,
            )

    def test_schedule_empty_milestone_id_fails(self):
        with pytest.raises(ValidationError):
            ScheduleMilestone(
                id="",
                name="Bad milestone",
                date="2026-03-01",
            )

    def test_schedule_empty_milestone_name_fails(self):
        with pytest.raises(ValidationError):
            ScheduleMilestone(
                id="MS-001",
                name="",
                date="2026-03-01",
            )

    def test_schedule_duplicate_activity_ids_fails(self):
        with pytest.raises(ValidationError, match="Duplicate activity IDs"):
            ScheduleV1(
                project_id="PRJ-DUP",
                activities=[
                    ScheduleActivity(id="ACT-001", name="Task A", duration_days=3),
                    ScheduleActivity(id="ACT-001", name="Task B", duration_days=5),
                ],
                metadata=ScheduleMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_schedule_with_predecessors_and_successors(self):
        sched = ScheduleV1(
            project_id="PRJ-004",
            activities=[
                ScheduleActivity(
                    id="ACT-001",
                    name="First task",
                    duration_days=3,
                    successors=["ACT-002"],
                ),
                ScheduleActivity(
                    id="ACT-002",
                    name="Second task",
                    duration_days=5,
                    predecessors=["ACT-001"],
                    resources=["Crew A", "Crane"],
                ),
            ],
            metadata=ScheduleMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
            ),
        )
        assert sched.activities[0].successors == ["ACT-002"]
        assert sched.activities[1].predecessors == ["ACT-001"]
        assert sched.activities[1].resources == ["Crew A", "Crane"]

    def test_activity_trade_is_free_text(self):
        """schedule-v1 types activity trade as a plain string, not the Trade enum."""
        act = ScheduleActivity(id="ACT-001", name="Slab pour", trade="concrete", duration_days=2)
        assert act.trade == "concrete"

    def test_unset_optional_fields_are_omitted(self):
        """No invented progress, criticality or milestone status."""
        act = ScheduleActivity(id="ACT-001", name="Excavation", duration_days=10)
        ms = ScheduleMilestone(id="MS-001", name="Dry-in", date="2026-06-01")
        assert act.percent_complete is None
        assert act.is_critical is None
        assert act.predecessors is None
        assert ms.is_met is None
        assert act.model_dump(exclude_none=True) == {
            "id": "ACT-001",
            "name": "Excavation",
            "durationDays": 10,
        }
        assert ms.model_dump(exclude_none=True) == {
            "id": "MS-001",
            "name": "Dry-in",
            "date": "2026-06-01",
        }


class TestChangeOrderV1:
    def test_valid_change_order(self):
        co = ChangeOrderV1(
            project_id="PRJ-001",
            change_order_number="CO-001",
            title="HVAC rerouting due to structural conflict",
            reason="design-change",
            status="draft",
            line_items=[
                ChangeOrderLineItem(
                    id="COL-001",
                    description="Reroute ductwork around beam",
                    trade="mechanical",
                    cost_impact=15000.00,
                    schedule_impact_days=3,
                    bom_item_ids=["LI-001", "LI-002"],
                ),
            ],
            total_cost_impact=15000.00,
            total_schedule_impact_days=3,
            related_rfis=["RFI-001"],
            metadata=ChangeOrderMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
                confidence=0.85,
            ),
        )
        data = co.model_dump(exclude_none=True)
        assert data["projectId"] == "PRJ-001"
        assert data["changeOrderNumber"] == "CO-001"
        assert data["reason"] == "design-change"
        assert data["status"] == "draft"
        assert data["lineItems"][0]["costImpact"] == 15000.00
        assert data["lineItems"][0]["scheduleImpactDays"] == 3
        assert data["totalCostImpact"] == 15000.00
        assert data["relatedRfis"] == ["RFI-001"]

    def test_change_order_round_trip(self):
        co_data = {
            "projectId": "PRJ-002",
            "changeOrderNumber": "CO-002",
            "title": "Add fire suppression",
            "reason": "code-compliance",
            "status": "submitted",
            "lineItems": [
                {
                    "id": "COL-001",
                    "description": "Fire suppression system",
                    "costImpact": 50000.00,
                },
            ],
            "totalCostImpact": 50000.00,
            "metadata": {
                "generatedBy": "estimator",
                "generatedAt": "2026-02-01T00:00:00Z",
            },
        }
        co = ChangeOrderV1.model_validate(co_data)
        data = co.model_dump(exclude_none=True)
        co2 = ChangeOrderV1.model_validate(data)
        assert co2.change_order_number == co.change_order_number
        assert co2.reason == "code-compliance"

    def test_change_order_empty_line_items_fails(self):
        with pytest.raises(ValidationError):
            ChangeOrderV1(
                project_id="PRJ-003",
                change_order_number="CO-003",
                title="Empty CO",
                reason="owner-request",
                status="draft",
                line_items=[],
                total_cost_impact=0.0,
                metadata=ChangeOrderMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_change_order_invalid_reason_fails(self):
        with pytest.raises(ValidationError):
            ChangeOrderV1(
                project_id="PRJ-004",
                change_order_number="CO-004",
                title="Bad reason",
                reason="nonexistent",
                status="draft",
                line_items=[
                    ChangeOrderLineItem(
                        id="COL-001",
                        description="Item",
                        cost_impact=1000.0,
                    ),
                ],
                total_cost_impact=1000.0,
                metadata=ChangeOrderMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_change_order_invalid_status_fails(self):
        with pytest.raises(ValidationError):
            ChangeOrderV1(
                project_id="PRJ-005",
                change_order_number="CO-005",
                title="Bad status",
                reason="design-change",
                status="nonexistent",
                line_items=[
                    ChangeOrderLineItem(
                        id="COL-001",
                        description="Item",
                        cost_impact=1000.0,
                    ),
                ],
                total_cost_impact=1000.0,
                metadata=ChangeOrderMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_change_order_schema_alias(self):
        assert ChangeOrderSchema is ChangeOrderV1

    def test_change_order_empty_line_item_id_fails(self):
        with pytest.raises(ValidationError):
            ChangeOrderLineItem(
                id="",
                description="Item",
                cost_impact=1000.0,
            )

    def test_change_order_empty_number_fails(self):
        with pytest.raises(ValidationError):
            ChangeOrderV1(
                project_id="PRJ-001",
                change_order_number="",
                title="Test",
                reason="design-change",
                status="draft",
                line_items=[
                    ChangeOrderLineItem(
                        id="COL-001",
                        description="Item",
                        cost_impact=1000.0,
                    ),
                ],
                total_cost_impact=1000.0,
                metadata=ChangeOrderMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_change_order_empty_title_fails(self):
        with pytest.raises(ValidationError):
            ChangeOrderV1(
                project_id="PRJ-001",
                change_order_number="CO-001",
                title="",
                reason="design-change",
                status="draft",
                line_items=[
                    ChangeOrderLineItem(
                        id="COL-001",
                        description="Item",
                        cost_impact=1000.0,
                    ),
                ],
                total_cost_impact=1000.0,
                metadata=ChangeOrderMetadata(
                    generated_by="test",
                    generated_at="2026-01-01T00:00:00Z",
                ),
            )

    def test_change_order_negative_cost(self):
        """Negative cost_impact is valid (credits/savings)."""
        co = ChangeOrderV1(
            project_id="PRJ-006",
            change_order_number="CO-006",
            title="Value engineering savings",
            reason="value-engineering",
            status="approved",
            line_items=[
                ChangeOrderLineItem(
                    id="COL-001",
                    description="Substitute cheaper material",
                    cost_impact=-5000.00,
                    schedule_impact_days=0,
                ),
            ],
            total_cost_impact=-5000.00,
            metadata=ChangeOrderMetadata(
                generated_by="test",
                generated_at="2026-01-01T00:00:00Z",
            ),
        )
        assert co.total_cost_impact == -5000.00

    def test_line_item_trade_is_free_text(self):
        """change-order-v1 types line item trade as a plain string."""
        item = ChangeOrderLineItem(
            id="COL-001", description="Rebar", trade="concrete", cost_impact=100.0
        )
        assert item.trade == "concrete"

    def test_unset_schedule_impact_is_omitted_not_zero(self):
        """A TBD schedule impact must not serialize as "0 days"."""
        co = ChangeOrderV1(
            project_id="PRJ-007",
            change_order_number="CO-007",
            title="Owner-requested finish upgrade",
            reason="owner-request",
            status="draft",
            line_items=[
                ChangeOrderLineItem(id="COL-001", description="Upgrade", cost_impact=1.0),
            ],
            total_cost_impact=1.0,
            metadata=ChangeOrderMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z"),
        )
        assert co.total_schedule_impact_days is None
        assert co.line_items[0].schedule_impact_days is None
        data = co.model_dump(exclude_none=True)
        assert "totalScheduleImpactDays" not in data
        assert "scheduleImpactDays" not in data["lineItems"][0]
        assert "relatedRfis" not in data
        assert "bomItemIds" not in data["lineItems"][0]


class TestUnknownFields:
    """Unknown properties survive a round trip (SPEC-003 §4.2 vendor extensions)."""

    def test_metadata_vendor_extensions_round_trip(self, sample_bom: dict):
        payload = {
            **sample_bom,
            "metadata": {
                **sample_bom["metadata"],
                "vendorExtensions": {"acme": {"takeoffRun": 42, "tags": ["a", "b"]}},
            },
        }
        bom = BOMV1.model_validate(payload)
        data = bom.model_dump(mode="json", by_alias=True, exclude_none=True)
        assert data["metadata"]["vendorExtensions"] == {
            "acme": {"takeoffRun": 42, "tags": ["a", "b"]}
        }

    def test_unknown_fields_kept_at_every_level(self):
        payload = {
            "projectId": "PRJ-001",
            "changeOrderNumber": "CO-001",
            "title": "T",
            "reason": "design-change",
            "status": "draft",
            "lineItems": [
                {"id": "COL-001", "description": "D", "costImpact": 1, "xAcmeCode": "Z9"},
            ],
            "totalCostImpact": 1,
            "xAcmeTopLevel": True,
            "metadata": {
                "generatedBy": "test",
                "generatedAt": "2026-01-01T00:00:00Z",
                "vendorExtensions": {"acme": {"baseline": "EST-12"}},
            },
        }
        co = ChangeOrderV1.model_validate(payload)
        assert co.model_dump(mode="json", by_alias=True, exclude_none=True) == payload


class TestDateFormats:
    """format: date / date-time fields validate the spec format and stay strings."""

    date_time = TypeAdapter(DateTimeString)
    full_date = TypeAdapter(DateString)

    @pytest.mark.parametrize(
        "value",
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T09:30:00.123456-05:00",
            "2026-01-01t09:30:00z",
            "2026-06-30T23:59:60Z",  # RFC 3339 leap second
            "2024-02-29T12:00:00+14:00",
        ],
    )
    def test_valid_date_time_is_kept_verbatim(self, value: str):
        assert self.date_time.validate_python(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "2026-01-01T09:30:00",  # naive: no offset
            "2026-01-01",  # date only
            "2026-01-01 09:30:00Z",  # space separator
            "2026-02-30T00:00:00Z",  # no such day
            "2026-01-01T24:00:00Z",
            "2026-01-01T09:60:00Z",
            "2026-01-01T09:30:00+24:00",
            "2026-01-01T09:30Z",  # seconds are mandatory
            "2026-01-01T09:30:00Z\n",
            "",
        ],
    )
    def test_invalid_date_time_fails(self, value: str):
        with pytest.raises(ValidationError):
            self.date_time.validate_python(value)

    def test_aware_datetime_is_serialized_as_rfc3339(self):
        value = datetime(2026, 1, 1, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
        assert self.date_time.validate_python(value) == "2026-01-01T09:30:00-05:00"

    def test_naive_datetime_fails(self):
        with pytest.raises(ValidationError, match="timezone offset"):
            self.date_time.validate_python(datetime(2026, 1, 1, 9, 30))

    def test_date_object_for_date_time_fails(self):
        with pytest.raises(ValidationError):
            self.date_time.validate_python(date(2026, 1, 1))

    @pytest.mark.parametrize("value", ["2026-01-01", "2024-02-29"])
    def test_valid_date_is_kept_verbatim(self, value: str):
        assert self.full_date.validate_python(value) == value

    @pytest.mark.parametrize(
        "value",
        ["2026-1-1", "20260101", "2026-13-01", "2026-02-29", "2026-01-01T00:00:00Z", ""],
    )
    def test_invalid_date_fails(self, value: str):
        with pytest.raises(ValidationError):
            self.full_date.validate_python(value)

    def test_date_object_is_serialized_as_full_date(self):
        assert self.full_date.validate_python(date(2026, 3, 15)) == "2026-03-15"

    def test_datetime_object_for_date_fails(self):
        with pytest.raises(ValidationError, match="date"):
            self.full_date.validate_python(datetime(2026, 3, 15, tzinfo=timezone.utc))

    @pytest.mark.parametrize("model", [BOMMetadata, EstimateMetadata, QuoteMetadata, RFIMetadata])
    def test_metadata_generated_at_requires_offset(self, model):
        with pytest.raises(ValidationError):
            model(generated_by="test", generated_at="2026-01-01T00:00:00")
        meta = model(generated_by="test", generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert meta.model_dump(mode="json")["generatedAt"] == "2026-01-01T00:00:00+00:00"

    @pytest.mark.parametrize("model", [ScheduleMetadata, ChangeOrderMetadata])
    def test_generated_at_without_spec_format_is_plain_string(self, model):
        """schedule-v1 / change-order-v1 declare no format on generatedAt."""
        meta = model(generated_by="test", generated_at="2026-01-01")
        assert meta.generated_at == "2026-01-01"

    def test_schedule_dates_without_spec_format_are_plain_strings(self):
        act = ScheduleActivity(
            id="ACT-001", name="Mobilize", duration_days=1, start_date="Week 1", end_date="Week 2"
        )
        ms = ScheduleMilestone(id="MS-001", name="NTP", date="TBD")
        assert (act.start_date, act.end_date, ms.date) == ("Week 1", "Week 2", "TBD")

    def test_model_date_fields(self):
        meta = EstimateMetadata(
            generated_by="test",
            generated_at="2026-01-01T00:00:00Z",
            pricing_date=date(2026, 1, 1),
        )
        assert meta.pricing_date == "2026-01-01"
        with pytest.raises(ValidationError):
            EstimateMetadata(
                generated_by="test", generated_at="2026-01-01T00:00:00Z", pricing_date="Jan 2026"
            )
        with pytest.raises(ValidationError):
            RFIV1(
                project_id="PRJ-001",
                subject="S",
                question="Q?",
                category="clarification",
                priority="low",
                references=[],
                due_date="next week",
                metadata=RFIMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z"),
            )
        with pytest.raises(ValidationError):
            QuoteV1(
                project_id="PRJ-001",
                supplier_name="ACME",
                quote_number="Q-1",
                valid_until="2026-03-01T00:00:00Z",
                line_items=[],
                summary=QuoteSummary(subtotal=0, tax_rate=0, tax_amount=0, freight=0, total=0),
                terms=QuoteTerms(
                    payment_terms="Net 30",
                    delivery_method="Pickup",
                    warranty="None",
                    return_policy="None",
                ),
                metadata=QuoteMetadata(generated_by="test", generated_at="2026-01-01T00:00:00Z"),
            )


class TestRFIAssigneeRole:
    @pytest.mark.parametrize(
        "role", ["architect", "engineer", "owner", "contractor", "subcontractor"]
    )
    def test_spec_roles_are_valid(self, role: str):
        assert RFIAssignee(role=role).role == role

    def test_unknown_role_fails(self):
        with pytest.raises(ValidationError):
            RFIAssignee(role="plumber")

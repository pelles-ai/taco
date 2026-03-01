"""CAIP data schemas — typed construction artifact definitions."""

from __future__ import annotations


class BOMSchema:
    """Bill of Materials schema (bom-v1)."""

    schema_id = "bom-v1"


class RFISchema:
    """Request for Information schema (rfi-v1)."""

    schema_id = "rfi-v1"


class EstimateSchema:
    """Cost estimate schema (estimate-v1)."""

    schema_id = "estimate-v1"


class ScheduleSchema:
    """Project schedule schema (schedule-v1)."""

    schema_id = "schedule-v1"


class QuoteSchema:
    """Supplier quote schema (quote-v1)."""

    schema_id = "quote-v1"


class ChangeOrderSchema:
    """Change order schema (change-order-v1)."""

    schema_id = "change-order-v1"

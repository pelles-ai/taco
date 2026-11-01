"""Token for the demo agents' ``/admin/skills`` endpoints.

The TACO SDK refuses to expose the admin endpoints without a token, because
they change the agent card every caller sees. The agents enable them only
when ``TACO_ADMIN_TOKEN`` is set, and the orchestrator sends the same token
when the dashboard adds a skill. ``make demo-env`` writes a random token to
``examples/.env`` and ``run_demo.py`` generates one for its run if none is set.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_VAR = "TACO_ADMIN_TOKEN"

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def admin_token() -> str | None:
    """The configured admin token, or ``None`` if admin is disabled."""
    return os.getenv(ENV_VAR) or None

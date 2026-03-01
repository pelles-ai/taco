"""CAIP Agent Registry — discover construction agents by trade, skill, and capability."""

from __future__ import annotations


class AgentRegistry:
    """Client for the CAIP Agent Registry."""

    def __init__(self, *, url: str) -> None:
        self.url = url

    def find(self, **filters) -> list:
        raise NotImplementedError("Agent discovery is not yet implemented")

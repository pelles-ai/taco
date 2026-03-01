"""CAIP Client — communicate with CAIP-compatible A2A agents."""

from __future__ import annotations


class CAIPClient:
    """Client for sending tasks to a CAIP-compatible agent."""

    def __init__(self, *, agent_url: str) -> None:
        self.agent_url = agent_url

    async def run_task(self, *, task_type: str, input: object) -> object:
        raise NotImplementedError("Task execution is not yet implemented")

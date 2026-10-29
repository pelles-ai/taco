"""Exceptions TACO task handlers can raise."""

from __future__ import annotations


class TacoTaskError(Exception):
    """Fail the current task with a message the caller is allowed to see.

    Raise it from a task handler for expected, caller-facing problems::

        if not input_data.get("lineItems"):
            raise TacoTaskError("bom-v1 input has no lineItems")

    The task ends ``failed`` with ``str(exc)`` as its status message. Any
    other exception also fails the task, but the caller only gets a generic
    message with an error id; the details go to the server log under that
    id. That keeps connection strings, file paths and stack details out of
    responses to other companies' agents.
    """

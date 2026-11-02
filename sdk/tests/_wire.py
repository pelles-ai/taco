"""Speak the A2A v0.3 or v1 JSON-RPC dialect to a TACO server.

Used by the wire-parity tests (ADR-0010): the same scenario runs once per
version. Requests are written by hand in each version's wire shape, so the
server's parsing of both dialects is what gets tested. Results are converted
back to the ``taco.types`` models with ``a2a.compat.v0_3.conversions``, so one
assertion covers both versions; ``Wire.raw_result`` keeps the wire JSON for
checks on the encoding itself.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from a2a.compat.v0_3 import conversions
from a2a.types import a2a_pb2 as pb
from google.protobuf.json_format import ParseDict

from taco.types import (
    Message,
    PushNotificationConfig,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

WIRE_VERSIONS = ("0.3", "1.0")

_METHODS = {
    "0.3": {
        "send": "message/send",
        "stream": "message/stream",
        "get": "tasks/get",
        "cancel": "tasks/cancel",
        "push_set": "tasks/pushNotificationConfig/set",
        "push_get": "tasks/pushNotificationConfig/get",
        "push_list": "tasks/pushNotificationConfig/list",
        "push_delete": "tasks/pushNotificationConfig/delete",
    },
    "1.0": {
        "send": "SendMessage",
        "stream": "SendStreamingMessage",
        "get": "GetTask",
        "cancel": "CancelTask",
        "push_set": "CreateTaskPushNotificationConfig",
        "push_get": "GetTaskPushNotificationConfig",
        "push_list": "ListTaskPushNotificationConfigs",
        "push_delete": "DeleteTaskPushNotificationConfig",
    },
}

StreamEvent = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent | Message


class WireError(Exception):
    """The server answered with a JSON-RPC error."""

    def __init__(self, error: dict[str, Any]) -> None:
        super().__init__(f"{error.get('code')}: {error.get('message')}")
        self.code = error.get("code")
        self.message = error.get("message", "")


@dataclass(frozen=True)
class Wire:
    version: str

    @property
    def v1(self) -> bool:
        return self.version == "1.0"

    def method(self, name: str) -> str:
        return _METHODS[self.version][name]

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        return {"A2A-Version": self.version, **(extra or {})}

    # -- requests ---------------------------------------------------------

    def message(
        self,
        data: dict[str, Any],
        *,
        context_id: str | None = None,
        reference_task_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        message: dict[str, Any] = {"messageId": uuid.uuid4().hex}
        if self.v1:
            message |= {"role": "ROLE_USER", "parts": [{"data": data}]}
        else:
            message |= {
                "kind": "message",
                "role": "user",
                "parts": [{"kind": "data", "data": data}],
            }
        if context_id:
            message["contextId"] = context_id
        if reference_task_ids:
            message["referenceTaskIds"] = reference_task_ids
        return message

    def send_params(
        self,
        task_type: str,
        data: dict[str, Any],
        *,
        return_immediately: bool = False,
        **message_kwargs: Any,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "message": self.message(data, **message_kwargs),
            "metadata": {"taskType": task_type},
        }
        if return_immediately:
            params["configuration"] = (
                {"returnImmediately": True} if self.v1 else {"blocking": False}
            )
        return params

    def body(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": self.method(name),
            "params": params,
        }

    async def post(
        self,
        http: httpx.AsyncClient,
        name: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await http.post("/", json=self.body(name, params), headers=self.headers(headers))

    async def call(
        self,
        http: httpx.AsyncClient,
        name: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        """The raw ``result`` of a call; raises ``WireError`` on an RPC error."""
        resp = await self.post(http, name, params, headers)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("error"):
            raise WireError(payload["error"])
        return payload.get("result")

    # -- normalised operations --------------------------------------------

    async def send(
        self, http: httpx.AsyncClient, task_type: str, data: dict[str, Any], **kw: Any
    ) -> Task:
        headers = kw.pop("headers", None)
        result = await self.call(http, "send", self.send_params(task_type, data, **kw), headers)
        return self.sent_task(result)

    async def get(self, http: httpx.AsyncClient, task_id: str) -> Task:
        return self.task(await self.call(http, "get", {"id": task_id}))

    async def cancel(self, http: httpx.AsyncClient, task_id: str) -> Task:
        return self.task(await self.call(http, "cancel", {"id": task_id}))

    async def stream(
        self, http: httpx.AsyncClient, task_type: str, data: dict[str, Any], **kw: Any
    ) -> list[StreamEvent]:
        body = self.body("stream", self.send_params(task_type, data, **kw))
        events: list[StreamEvent] = []
        async with http.stream("POST", "/", json=body, headers=self.headers()) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = json.loads(line[len("data:") :])
                if payload.get("error"):
                    raise WireError(payload["error"])
                events.append(self.stream_event(payload["result"]))
        return events

    async def push_set(
        self,
        http: httpx.AsyncClient,
        task_id: str,
        config_id: str,
        url: str,
        token: str | None = None,
    ) -> PushNotificationConfig:
        config: dict[str, Any] = {"id": config_id, "url": url}
        if token:
            config["token"] = token
        params = (
            {"taskId": task_id, **config}
            if self.v1
            else {"taskId": task_id, "pushNotificationConfig": config}
        )
        return self.push_config(await self.call(http, "push_set", params))

    async def push_get(
        self, http: httpx.AsyncClient, task_id: str, config_id: str
    ) -> PushNotificationConfig:
        params = (
            {"taskId": task_id, "id": config_id}
            if self.v1
            else {"id": task_id, "pushNotificationConfigId": config_id}
        )
        return self.push_config(await self.call(http, "push_get", params))

    async def push_list(
        self, http: httpx.AsyncClient, task_id: str
    ) -> list[PushNotificationConfig]:
        params = {"taskId": task_id} if self.v1 else {"id": task_id}
        result = await self.call(http, "push_list", params)
        items = result.get("configs", []) if self.v1 else result
        return [self.push_config(item) for item in items]

    async def push_delete(self, http: httpx.AsyncClient, task_id: str, config_id: str) -> None:
        params = (
            {"taskId": task_id, "id": config_id}
            if self.v1
            else {"id": task_id, "pushNotificationConfigId": config_id}
        )
        await self.call(http, "push_delete", params)

    # -- result conversion --------------------------------------------------

    def sent_task(self, result: dict[str, Any]) -> Task:
        """The task in a send result (v1 wraps it as ``{"task": ...}``)."""
        return self.task(result["task"] if self.v1 else result)

    def task(self, raw: dict[str, Any]) -> Task:
        if self.v1:
            return conversions.to_compat_task(ParseDict(raw, pb.Task(), ignore_unknown_fields=True))
        return Task.model_validate(raw)

    def stream_event(self, raw: dict[str, Any]) -> StreamEvent:
        if not self.v1:
            kind = raw.get("kind")
            model = {
                "task": Task,
                "status-update": TaskStatusUpdateEvent,
                "artifact-update": TaskArtifactUpdateEvent,
                "message": Message,
            }[kind]
            return model.model_validate(raw)
        event = ParseDict(raw, pb.StreamResponse(), ignore_unknown_fields=True)
        which = event.WhichOneof("payload")
        if which == "task":
            return conversions.to_compat_task(event.task)
        if which == "status_update":
            return conversions.to_compat_task_status_update_event(event.status_update)
        if which == "artifact_update":
            return conversions.to_compat_task_artifact_update_event(event.artifact_update)
        return conversions.to_compat_message(event.message)

    def push_config(self, raw: dict[str, Any]) -> PushNotificationConfig:
        if self.v1:
            core = ParseDict(raw, pb.TaskPushNotificationConfig(), ignore_unknown_fields=True)
            return conversions.to_compat_task_push_notification_config(
                core
            ).push_notification_config
        return PushNotificationConfig.model_validate(raw.get("pushNotificationConfig", raw))

    def raw_artifact_data(self, send_result: dict[str, Any]) -> dict[str, Any]:
        """The first artifact's data part, exactly as it was on the wire."""
        task = send_result["task"] if self.v1 else send_result
        return task["artifacts"][0]["parts"][0]["data"]

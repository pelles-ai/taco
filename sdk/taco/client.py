"""TACO Client — communicate with TACO-compatible A2A agents."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator, Mapping
from typing import Any

try:
    import httpx
except ImportError:
    raise ImportError(
        "Client dependencies not installed. Install with: pip install 'taco-agent[client]'"
    ) from None

from a2a.compat.v0_3 import conversions
from a2a.types import a2a_pb2 as pb
from google.protobuf.json_format import MessageToDict, ParseDict

from ._compat import make_data_part, make_message, restore_integers
from .types import (
    X_CONSTRUCTION_EXTENSION_URI,
    AgentCard,
    DataPart,
    Message,
    PushNotificationConfig,
    Task,
    with_v03_card_fields,
)

_log = logging.getLogger("taco.client")

# A2A protocol version this client speaks. Sent on every request as the
# ``A2A-Version`` header so peers can negotiate (the v1 protocol added
# this header explicitly; v0.3 servers ignore it harmlessly).
A2A_PROTOCOL_VERSION = "0.3"

# Every request asks the peer to activate TACO's x-construction extension.
# A2A v1 names the header ``A2A-Extensions``; v0.3 named it
# ``X-A2A-Extensions``. This client speaks v0.3, so it sends both, as the
# a2a-sdk client does.
EXTENSION_HEADERS = ("A2A-Extensions", "X-A2A-Extensions")

#: Values for ``TacoClient(protocol=...)``. ``"0.3"`` and ``"1.0"`` pick the
#: A2A wire version; ``"auto"`` reads the agent card and uses v1 when the card
#: lists a v1 JSON-RPC interface at the agent's endpoint (ADR-0010).
PROTOCOLS = ("auto", "1.0", "0.3")

# v0.3 JSON-RPC method names and their A2A v1 equivalents.
_V1_METHODS = {
    "message/send": "SendMessage",
    "message/stream": "SendStreamingMessage",
    "tasks/get": "GetTask",
    "tasks/cancel": "CancelTask",
    "tasks/pushNotificationConfig/set": "CreateTaskPushNotificationConfig",
    "tasks/pushNotificationConfig/get": "GetTaskPushNotificationConfig",
    "tasks/pushNotificationConfig/list": "ListTaskPushNotificationConfigs",
    "tasks/pushNotificationConfig/delete": "DeleteTaskPushNotificationConfig",
}

# JSON-RPC errors for a method or version the agent does not speak: -32601
# (method not found) and A2A v1's -32009 (version not supported).
_VERSION_REJECTED = frozenset({-32601, -32009})


def _check_protocol(protocol: str) -> str:
    if protocol not in PROTOCOLS:
        raise ValueError(f"protocol must be one of {', '.join(PROTOCOLS)}, not {protocol!r}")
    return protocol


def _protocol_for_card(card: AgentCard | Mapping[str, Any], agent_url: str | None = None) -> str:
    """The A2A wire version to use with an agent, read from its card.

    ``"1.0"`` when the card lists an A2A 1.x JSON-RPC interface at the
    card's ``url`` (the endpoint v0.3 clients use) or at ``agent_url`` (the
    endpoint this client posts to); ``"0.3"`` otherwise, including for every
    card without ``supportedInterfaces``.
    """
    url: str | None
    if isinstance(card, AgentCard):
        url = card.url
        interfaces = (card.model_extra or {}).get("supportedInterfaces")
    else:
        data = with_v03_card_fields(dict(card))
        url = data.get("url")
        interfaces = data.get("supportedInterfaces")
    endpoints = {str(u).rstrip("/") for u in (url, agent_url) if u}
    for interface in interfaces or []:
        if not isinstance(interface, Mapping):
            continue
        major = str(interface.get("protocolVersion") or "").split(".")[0]
        if (
            major == "1"
            and interface.get("protocolBinding", "JSONRPC") == "JSONRPC"
            and str(interface.get("url") or "").rstrip("/") in endpoints
        ):
            return "1.0"
    return "0.3"


def _extension_uris(value: str) -> list[str]:
    return [uri.strip() for uri in value.split(",") if uri.strip()]


def _merge_protocol_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Add the protocol headers to caller headers.

    A caller's ``A2A-Version`` wins. Extension URIs a caller lists in
    either extensions header are added to ``x-construction``, not
    substituted for it.
    """
    merged: dict[str, str] = {"A2A-Version": A2A_PROTOCOL_VERSION}
    uris = [X_CONSTRUCTION_EXTENSION_URI]
    for name, value in (headers or {}).items():
        if name.lower() in {h.lower() for h in EXTENSION_HEADERS}:
            uris += [uri for uri in _extension_uris(value) if uri not in uris]
        else:
            merged[name] = value
    for name in EXTENSION_HEADERS:
        merged[name] = ", ".join(uris)
    return merged


class TacoClientError(Exception):
    """Base exception for TACO client errors."""


class RpcError(TacoClientError):
    """A JSON-RPC error returned by the remote agent."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.rpc_message = message
        self.data = data
        super().__init__(f"RPC error {code}: {message}")


class ProtocolVersionError(RpcError):
    """The agent does not answer the A2A version or method the client used.

    Raised for JSON-RPC ``-32601`` (method not found) and ``-32009`` (A2A
    v1's version not supported). :attr:`protocol` is the version the client
    spoke and :attr:`method` the method it sent. With ``protocol="auto"`` it
    means the agent's card lists a version the agent does not serve.
    """

    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None,
        *,
        protocol: str,
        method: str,
    ) -> None:
        super().__init__(code, message, data)
        self.protocol = protocol
        self.method = method
        self.args = (
            f"Agent rejected A2A {protocol} method {method} (RPC error {code}: {message})",
        )


class MessageReplyError(TacoClientError):
    """The agent answered with a ``Message`` where a ``Task`` was expected.

    TACO agents always return a Task, but other A2A agents may reply to
    ``message/send`` with a plain Message. The reply is on :attr:`reply`.
    """

    def __init__(self, reply: Message) -> None:
        self.reply = reply
        super().__init__("Agent replied with a Message instead of a Task")


def _restore_task_integers(task: Task) -> Task:
    """Apply :func:`restore_integers` to every DataPart in ``task``."""
    messages = [*(task.history or []), *([task.status.message] if task.status.message else [])]
    parts = [p for m in messages for p in m.parts]
    parts += [p for a in task.artifacts or [] for p in a.parts]
    for part in parts:
        if isinstance(part.root, DataPart):
            part.root.data = restore_integers(part.root.data)
    return task


def _restore_message_integers(message: Message) -> Message:
    for part in message.parts:
        if isinstance(part.root, DataPart):
            part.root.data = restore_integers(part.root.data)
    return message


# -- A2A v1 wire shapes ----------------------------------------------------
#
# Requests are written in the v1 shape directly; responses are parsed into
# a2a-sdk's v1 protobuf types and converted back to the v0.3 models TacoClient
# returns. The protobuf round trip turns whole numbers into floats, so
# integers are restored after each conversion.


def _to_v1_message(message: dict[str, Any]) -> dict[str, Any]:
    """A v0.3 message dict, as TacoClient builds it, in the v1 JSON shape.

    TacoClient only sends data parts, whose v1 form is the v0.3 one without
    ``kind``. Copying them as they are keeps whole numbers integers on the
    wire.
    """
    v1 = {key: value for key, value in message.items() if key != "kind"}
    v1["role"] = f"ROLE_{str(message['role']).upper()}"
    v1["parts"] = [
        {key: value for key, value in part.items() if key != "kind"} for part in message["parts"]
    ]
    return v1


def _from_v1_task(raw: dict[str, Any]) -> Task:
    core = ParseDict(raw, pb.Task(), ignore_unknown_fields=True)
    return _restore_task_integers(conversions.to_compat_task(core))


def _from_v1_send_result(raw: dict[str, Any]) -> Task | Message:
    """The task (or message) in a v1 ``SendMessage`` result."""
    response = ParseDict(raw, pb.SendMessageResponse(), ignore_unknown_fields=True)
    if response.WhichOneof("payload") == "message":
        return _restore_message_integers(conversions.to_compat_message(response.message))
    return _restore_task_integers(conversions.to_compat_task(response.task))


def _from_v1_stream_result(raw: dict[str, Any]) -> dict[str, Any]:
    """A v1 stream event as the v0.3 event dict :meth:`TacoClient.stream_message` yields."""
    event = ParseDict(raw, pb.StreamResponse(), ignore_unknown_fields=True)
    which = event.WhichOneof("payload")
    model: Any
    if which == "task":
        model = conversions.to_compat_task(event.task)
    elif which == "status_update":
        model = conversions.to_compat_task_status_update_event(event.status_update)
    elif which == "artifact_update":
        model = conversions.to_compat_task_artifact_update_event(event.artifact_update)
    elif which == "message":
        model = conversions.to_compat_message(event.message)
    else:
        return raw
    return restore_integers(model.model_dump(mode="json", by_alias=True, exclude_none=True))


def _to_v1_push_config(task_id: str, config: PushNotificationConfig) -> dict[str, Any]:
    core = conversions.to_core_push_notification_config(config)
    core.task_id = task_id
    return MessageToDict(core)


def _from_v1_push_config(raw: dict[str, Any]) -> PushNotificationConfig:
    core = ParseDict(raw, pb.TaskPushNotificationConfig(), ignore_unknown_fields=True)
    return conversions.to_compat_task_push_notification_config(core).push_notification_config


class TacoClient:
    """Async client for sending tasks to a TACO-compatible agent.

    ``headers`` are sent on every request (for example an
    ``Authorization`` header for an agent that requires a token);
    per-call ``headers`` arguments are merged on top of them.

    ``protocol`` picks the A2A wire version (ADR-0010):

    - ``"0.3"`` (the default) sends ``message/send``, ``tasks/get`` and the
      other v0.3 methods, as every TACO release has.
    - ``"1.0"`` sends the v1 methods (``SendMessage``, ``GetTask``, ...) with
      ``A2A-Version: 1.0``.
    - ``"auto"`` reads the agent card (fetched once, on the first call, and
      cached) and uses ``"1.0"`` when the card lists an A2A v1 JSON-RPC
      interface at the agent's endpoint, as TACO agents from 0.7 do, and
      ``"0.3"`` otherwise or when the card cannot be read.

    Every method returns the same ``taco.types`` models, and
    :meth:`stream_message` yields the same event dicts, whichever version is
    on the wire. An agent that does not answer the version used raises
    :class:`ProtocolVersionError`.
    """

    def __init__(
        self,
        *,
        agent_url: str,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 120.0,
        headers: dict[str, str] | None = None,
        protocol: str = "0.3",
    ) -> None:
        self.agent_url = agent_url.rstrip("/")
        self.protocol = _check_protocol(protocol)
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._agent_card: AgentCard | None = None
        self._card_unavailable = False
        self._default_headers = dict(headers or {})

    def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Protocol header, then client defaults, then per-call headers."""
        return _merge_protocol_headers({**self._default_headers, **(headers or {})})

    # -- context manager --

    async def __aenter__(self) -> TacoClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- discovery --

    async def discover(self) -> AgentCard:
        """Fetch and cache the agent's AgentCard.

        Tries the A2A v0.3+ path ``/.well-known/agent-card.json`` first,
        falling back to the legacy ``/.well-known/agent.json`` on 404.
        Sends the ``A2A-Version`` header so v1 peers can negotiate.
        """
        headers = self._headers()
        resp = await self._client.get(
            f"{self.agent_url}/.well-known/agent-card.json",
            headers=headers,
        )
        if resp.status_code == 404:
            resp = await self._client.get(
                f"{self.agent_url}/.well-known/agent.json",
                headers=headers,
            )
        resp.raise_for_status()
        self._agent_card = AgentCard.model_validate(resp.json())
        return self._agent_card

    @property
    def agent_card(self) -> AgentCard | None:
        return self._agent_card

    # -- JSON-RPC helpers --

    def _rpc_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

    async def _rpc_call(
        self,
        method: str,
        params: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = self._rpc_request(method, params)
        resp = await self._client.post(
            f"{self.agent_url}/",
            json=payload,
            headers=self._headers(headers),
        )
        resp.raise_for_status()
        body = resp.json()
        if "error" in body and body["error"] is not None:
            err = body["error"]
            raise RpcError(err["code"], err["message"], err.get("data"))
        # Peers on A2A v1 may send whole numbers as 120.0 (protobuf Struct).
        return restore_integers(body.get("result", {}))

    async def wire_protocol(self) -> str:
        """The A2A version this client speaks to the agent: ``"1.0"`` or ``"0.3"``.

        With ``protocol="auto"`` the first call reads the agent card (see
        :meth:`discover`). An agent without a readable card (an HTTP error
        status, or a body that is not a valid card) is spoken to in
        ``"0.3"``, which every TACO agent answers, and its card is not asked
        for again. A connection error propagates, and the card is fetched
        again on the next call.
        """
        if self.protocol != "auto":
            return self.protocol
        if self._agent_card is None and not self._card_unavailable:
            try:
                await self.discover()
            except (httpx.HTTPStatusError, ValueError) as exc:
                self._card_unavailable = True
                _log.warning(
                    "Could not read the agent card at %s (%s); speaking A2A 0.3",
                    self.agent_url,
                    exc,
                )
        if self._agent_card is None:
            return "0.3"
        return _protocol_for_card(self._agent_card, self.agent_url)

    async def _call(
        self,
        protocol: str,
        method: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Call ``method`` (its v0.3 name, or a v1-only one) in ``protocol``."""
        if protocol == "1.0":
            method = _V1_METHODS.get(method, method)
            headers = {"A2A-Version": "1.0", **(headers or {})}
        try:
            return await self._rpc_call(method, params, headers=headers)
        except RpcError as exc:
            if exc.code in _VERSION_REJECTED and not isinstance(exc, ProtocolVersionError):
                raise ProtocolVersionError(
                    exc.code, exc.rpc_message, exc.data, protocol=protocol, method=method
                ) from exc
            raise

    # -- task operations --

    @staticmethod
    def _message_params(
        task_type: str,
        input_data: dict[str, Any],
        context_id: str | None = None,
        reference_task_ids: list[str] | None = None,
        return_immediately: bool = False,
        protocol: str = "0.3",
    ) -> dict[str, Any]:
        """Build the common params dict for sending and streaming a message."""
        msg = make_message(
            "user",
            [make_data_part(input_data)],
            reference_task_ids=reference_task_ids,
            context_id=context_id,
        )
        message = msg.model_dump(mode="json", by_alias=True, exclude_none=True)
        v1 = protocol == "1.0"
        params: dict[str, Any] = {
            "message": _to_v1_message(message) if v1 else message,
            "metadata": {"taskType": task_type},
        }
        if return_immediately:
            # Tell the server not to wait for a terminal task state: v1's
            # ``returnImmediately``, v0.3's ``blocking: false``.
            params["configuration"] = {"returnImmediately": True} if v1 else {"blocking": False}
        return params

    async def send_message(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        reference_task_ids: list[str] | None = None,
        return_immediately: bool = False,
        headers: dict[str, str] | None = None,
    ) -> Task:
        """Send a message to the agent and return the resulting Task.

        ``reference_task_ids`` (A2A v1) links this message to prior
        tasks — e.g. an RFI response references the originating RFI
        task, a change-order approval references the proposal task.

        When ``return_immediately`` is ``True``, the server returns the
        Task as soon as it accepts the message (typically in
        ``submitted`` / ``working`` state) rather than waiting for the
        terminal state. Useful for fire-and-forget workflows where the
        caller plans to poll via :meth:`get_task` / :meth:`list_tasks`,
        or where progress is observed elsewhere (push notifications,
        the Monitor UI, an event bus).
        """
        protocol = await self.wire_protocol()
        params = self._message_params(
            task_type, input_data, context_id, reference_task_ids, return_immediately, protocol
        )
        result = await self._call(protocol, "message/send", params, headers)
        return self._task_result(result, protocol)

    @staticmethod
    def _task_result(result: dict[str, Any], protocol: str = "0.3") -> Task:
        reply: Task | Message
        if protocol == "1.0":
            reply = _from_v1_send_result(result)
        elif isinstance(result, dict) and result.get("kind") == "message":
            reply = Message.model_validate(result)
        else:
            reply = Task.model_validate(result)
        if isinstance(reply, Message):
            raise MessageReplyError(reply)
        return reply

    def _task(self, result: dict[str, Any], protocol: str) -> Task:
        return _from_v1_task(result) if protocol == "1.0" else Task.model_validate(result)

    async def get_task(self, task_id: str, *, headers: dict[str, str] | None = None) -> Task:
        """Retrieve a task by ID."""
        protocol = await self.wire_protocol()
        result = await self._call(protocol, "tasks/get", {"id": task_id}, headers)
        return self._task(result, protocol)

    async def cancel_task(self, task_id: str, *, headers: dict[str, str] | None = None) -> Task:
        """Cancel a task by ID."""
        protocol = await self.wire_protocol()
        result = await self._call(protocol, "tasks/cancel", {"id": task_id}, headers)
        return self._task(result, protocol)

    async def run_task(
        self,
        *,
        task_type: str,
        input_data: dict[str, Any],
        reference_task_ids: list[str] | None = None,
        return_immediately: bool = False,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Legacy convenience — send a message and return raw result dict.

        The dict is in the v0.3 shape in either protocol: a v1 result is
        converted, so callers see ``"state": "completed"`` either way.
        """
        protocol = await self.wire_protocol()
        params = self._message_params(
            task_type,
            input_data,
            reference_task_ids=reference_task_ids,
            return_immediately=return_immediately,
            protocol=protocol,
        )
        result = await self._call(protocol, "message/send", params, headers)
        if protocol == "1.0":
            reply = _from_v1_send_result(result)
            return reply.model_dump(mode="json", by_alias=True, exclude_none=True)
        return result

    async def list_tasks(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        context_id: str | None = None,
        include_artifacts: bool = False,
        headers: dict[str, str] | None = None,
    ) -> tuple[list[Task], str | None]:
        """List tasks visible to this caller via the v1 ``ListTasks`` RPC.

        Returns ``(tasks, next_cursor)``. Pass ``next_cursor`` back as
        ``cursor`` on a subsequent call to fetch the next page; a
        ``None`` cursor means there are no more results. ``ListTasks``
        leaves artifacts out unless ``include_artifacts`` is ``True``.

        ``ListTasks`` was added in A2A v1.0, so this method always speaks
        v1, whatever ``protocol`` is: v0.3-only peers reject it with
        :class:`ProtocolVersionError`.
        """
        params: dict[str, Any] = {}
        if cursor is not None:
            params["pageToken"] = cursor
        if limit is not None:
            params["pageSize"] = limit
        if context_id is not None:
            params["contextId"] = context_id
        if include_artifacts:
            params["includeArtifacts"] = True

        result = await self._call("1.0", "ListTasks", params, headers)
        tasks = [_from_v1_task(raw) for raw in result.get("tasks", [])]
        next_cursor = result.get("nextPageToken") or None
        return tasks, next_cursor

    # -- push notification configs (A2A v1: multiple per task) --

    async def create_push_config(
        self,
        task_id: str,
        url: str,
        *,
        token: str | None = None,
        authentication: dict[str, Any] | None = None,
        config_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> PushNotificationConfig:
        """Subscribe a webhook to receive push events for ``task_id``.

        A task can carry multiple push configs in A2A v1 — pass distinct
        ``config_id`` values to register multiple subscribers (e.g. one
        for the project owner's dashboard, another for an audit log).
        """
        config = PushNotificationConfig(
            id=config_id,
            url=url,
            token=token,
            authentication=authentication,
        )
        protocol = await self.wire_protocol()
        if protocol == "1.0":
            params = _to_v1_push_config(task_id, config)
        else:
            params = {
                "taskId": task_id,
                "pushNotificationConfig": config.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                ),
            }
        result = await self._call(protocol, "tasks/pushNotificationConfig/set", params, headers)
        if protocol == "1.0":
            return _from_v1_push_config(result)
        # v0.3 response wraps the config inside TaskPushNotificationConfig
        cfg_payload = result.get("pushNotificationConfig", result)
        return PushNotificationConfig.model_validate(cfg_payload)

    async def list_push_configs(
        self,
        task_id: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> list[PushNotificationConfig]:
        """Return every push config currently registered for ``task_id``."""
        protocol = await self.wire_protocol()
        params = {"taskId": task_id} if protocol == "1.0" else {"id": task_id}
        result = await self._call(protocol, "tasks/pushNotificationConfig/list", params, headers)
        if protocol == "1.0":
            return [_from_v1_push_config(raw) for raw in result.get("configs", [])]
        items = result if isinstance(result, list) else result.get("configs", [])
        configs: list[PushNotificationConfig] = []
        for raw in items:
            cfg_payload = raw.get("pushNotificationConfig", raw) if isinstance(raw, dict) else raw
            configs.append(PushNotificationConfig.model_validate(cfg_payload))
        return configs

    async def get_push_config(
        self,
        task_id: str,
        config_id: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> PushNotificationConfig:
        """Fetch a single push config by its id."""
        protocol = await self.wire_protocol()
        result = await self._call(
            protocol,
            "tasks/pushNotificationConfig/get",
            self._push_config_ref(task_id, config_id, protocol),
            headers,
        )
        if protocol == "1.0":
            return _from_v1_push_config(result)
        cfg_payload = result.get("pushNotificationConfig", result)
        return PushNotificationConfig.model_validate(cfg_payload)

    async def delete_push_config(
        self,
        task_id: str,
        config_id: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Unsubscribe a webhook from ``task_id``. No-op if already gone."""
        protocol = await self.wire_protocol()
        await self._call(
            protocol,
            "tasks/pushNotificationConfig/delete",
            self._push_config_ref(task_id, config_id, protocol),
            headers,
        )

    @staticmethod
    def _push_config_ref(task_id: str, config_id: str, protocol: str) -> dict[str, str]:
        if protocol == "1.0":
            return {"taskId": task_id, "id": config_id}
        return {"id": task_id, "pushNotificationConfigId": config_id}

    # -- streaming --

    async def stream_message(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        reference_task_ids: list[str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a streaming message and yield SSE event dicts.

        Each yielded dict has ``event`` (str) and ``data`` (parsed JSON).
        ``reference_task_ids`` (A2A v1) links this message to prior tasks.
        ``data`` is the JSON-RPC response for one event, its ``result`` in
        the v0.3 shape (``"kind": "status-update"``, ``"state": "working"``)
        in either protocol.
        """
        protocol = await self.wire_protocol()
        params = self._message_params(
            task_type, input_data, context_id, reference_task_ids, protocol=protocol
        )
        method = "message/stream"
        if protocol == "1.0":
            method = _V1_METHODS[method]
            headers = {"A2A-Version": "1.0", **(headers or {})}
        payload = self._rpc_request(method, params)
        async with self._client.stream(
            "POST",
            f"{self.agent_url}/",
            json=payload,
            headers=self._headers(headers),
        ) as resp:
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("application/json"):
                # The agent answered with one JSON-RPC response instead of a
                # stream: an error, such as a method or version it lacks.
                body = json.loads(await resp.aread())
                error = body.get("error") if isinstance(body, dict) else None
                if error:
                    code = error.get("code")
                    if code in _VERSION_REJECTED:
                        raise ProtocolVersionError(
                            code,
                            error.get("message", ""),
                            error.get("data"),
                            protocol=protocol,
                            method=method,
                        )
                    raise RpcError(code, error.get("message", ""), error.get("data"))
            event_type = "message"
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    data_str = line[len("data:") :].strip()
                    try:
                        data = restore_integers(json.loads(data_str))
                        if protocol == "1.0" and isinstance(data, dict):
                            result = data.get("result")
                            if isinstance(result, dict):
                                data = {**data, "result": _from_v1_stream_result(result)}
                    except (json.JSONDecodeError, ValueError) as parse_err:
                        _log.warning(
                            "Failed to parse SSE data as JSON (event=%s): %s",
                            event_type,
                            parse_err,
                        )
                        data = data_str
                    yield {"event": event_type, "data": data}
                    event_type = "message"

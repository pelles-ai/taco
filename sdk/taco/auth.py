"""Bearer-token authentication for TACO agents.

TACO's security model (``spec/security.md``) asks agents to validate a
bearer token on every task request, answer HTTP 401 when it is missing or
invalid and HTTP 403 when it lacks the scope for the requested task type
(``taco:task:<taskType>``). Token *validation* is deployment-specific (JWT
signatures, introspection, API keys), so the SDK takes a verifier function
and does the rest::

    from taco import A2AServer, AuthContext

    async def verify(token: str) -> AuthContext | None:
        claims = await my_idp.introspect(token)  # your code
        if not claims.active:
            return None
        return AuthContext(subject=claims.sub, scopes=frozenset(claims.scope.split()))

    server = A2AServer(card, token_verifier=verify)

Only the JSON-RPC endpoint is protected; the agent card, ``/health`` and
the monitor (which has its own token) stay as they are. Each caller's
``subject`` becomes the task owner, so the a2a-sdk task stores only show
callers their own tasks. Inside a handler, :func:`current_auth` returns the
caller's :class:`AuthContext`.

A project-scoped agent (``x-construction.security.projectScoped: true``, or
``require_project_scope=True``) also answers HTTP 403 unless the token
covers the ``projectId`` in the request data (``taco:project:<id>:write``).

Scopes follow ``taco:{dimension}:{value}[:{action}]``: an omitted action
means ``write``, and ``admin`` covers ``write``, which covers ``read``.
"""

from __future__ import annotations

import contextvars
import functools
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .server import A2AServer

logger = logging.getLogger("taco.auth")

TASK_SCOPE_PREFIX = "taco:task:"
PROJECT_SCOPE_PREFIX = "taco:project:"

# Scope actions, weakest first. A granted action covers every weaker one.
_ACTIONS = ("read", "write", "admin")

# JSON-RPC methods (v0.3 compat and v1) that start a task.
_TASK_METHODS = frozenset({"message/send", "message/stream", "SendMessage", "SendStreamingMessage"})


@dataclass(frozen=True)
class AuthContext:
    """Who is calling, as established by a :data:`TokenVerifier`.

    Attributes:
        subject: Stable caller identity (for example the token's ``sub``).
            Tasks are stored per subject.
        scopes: Granted scopes, e.g. ``{"taco:task:estimate"}``.
        claims: Any other token claims your handlers need.
    """

    subject: str
    scopes: frozenset[str] = frozenset()
    claims: dict[str, Any] = field(default_factory=dict)

    def has_scope(self, scope: str) -> bool:
        """Whether ``scope`` was granted exactly as written."""
        return scope in self.scopes

    def allows(self, scope: str) -> bool:
        """Whether the granted scopes cover ``scope`` under the TACO scope rules.

        ``taco:project:PRJ-1`` (action omitted, so ``write``) is covered by
        ``taco:project:PRJ-1``, ``taco:project:PRJ-1:write`` or
        ``taco:project:PRJ-1:admin``, but not by ``taco:project:PRJ-1:read``.
        Scopes without a TACO action must match exactly.
        """
        base, action = _split_action(scope)
        needed = _ACTIONS.index(action)
        return any(
            granted_base == base and _ACTIONS.index(granted_action) >= needed
            for granted_base, granted_action in map(_split_action, self.scopes)
        )


def _split_action(scope: str) -> tuple[str, str]:
    base, _, action = scope.rpartition(":")
    if base and action in _ACTIONS:
        return base, action
    return scope, "write"


TokenVerifier = Callable[[str], Awaitable["AuthContext | None"]]
"""``async (token) -> AuthContext | None``; return ``None`` to reject."""

_current_auth: contextvars.ContextVar[AuthContext | None] = contextvars.ContextVar(
    "taco_current_auth", default=None
)


def current_auth() -> AuthContext | None:
    """The calling peer's :class:`AuthContext` inside a task handler.

    ``None`` when the server has no ``token_verifier``.
    """
    return _current_auth.get()


def task_scope(task_type: str) -> str:
    """The scope a token needs to request ``task_type`` (``taco:task:<type>``)."""
    return f"{TASK_SCOPE_PREFIX}{task_type}"


def project_scope(project_id: str, action: str = "write") -> str:
    """A project scope, e.g. ``taco:project:PRJ-0042:write``.

    Submitting a task for a project needs ``write`` (the default).
    """
    if action not in _ACTIONS:
        raise ValueError(f"action must be one of {_ACTIONS}, got {action!r}")
    return f"{PROJECT_SCOPE_PREFIX}{project_id}:{action}"


@functools.cache
def _credentials_class() -> Any:
    from starlette.authentication import AuthCredentials

    class TacoCredentials(AuthCredentials):
        """Starlette credentials that also carry the :class:`AuthContext`."""

        def __init__(self, context: AuthContext) -> None:
            super().__init__(sorted(context.scopes))
            self.context = context

    return TacoCredentials


def _starlette_auth_objects(auth: AuthContext) -> tuple[Any, Any]:
    """``scope["auth"]`` / ``scope["user"]`` values for the a2a-sdk.

    The a2a-sdk call-context builder reads ``request.user`` for the task
    owner and copies ``request.auth`` into the call context's state.
    """
    from starlette.authentication import SimpleUser

    return _credentials_class()(auth), SimpleUser(auth.subject)


def auth_from_call_context(call_context: Any) -> AuthContext | None:
    """The :class:`AuthContext` the middleware attached to an a2a-sdk call."""
    state = getattr(call_context, "state", None) or {}
    return getattr(state.get("auth"), "context", None)


def _set_current_auth(auth: AuthContext | None) -> contextvars.Token[AuthContext | None]:
    return _current_auth.set(auth)


class BearerAuthMiddleware:
    """ASGI middleware that enforces a :data:`TokenVerifier` on ``POST /``."""

    def __init__(
        self,
        app: Any,
        *,
        server: A2AServer,
        verifier: TokenVerifier,
        require_task_scope: bool = True,
        require_project_scope: bool | None = None,
        rpc_path: str = "/",
    ) -> None:
        self.app = app
        self.server = server
        self.verifier = verifier
        self.require_task_scope = require_task_scope
        self.require_project_scope = require_project_scope
        self.rpc_path = rpc_path

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] != self.rpc_path:
            await self.app(scope, receive, send)
            return
        if scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        # Read the body once (to find the JSON-RPC id, method and task
        # type), then replay it to the app.
        received: list[Any] = []
        body_parts: list[bytes] = []
        while True:
            message = await receive()
            received.append(message)
            if message["type"] != "http.request":
                break
            body_parts.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

        async def replay_receive() -> Any:
            if received:
                return received.pop(0)
            return await receive()

        try:
            payload = json.loads(b"".join(body_parts))
        except ValueError:
            payload = None
        rpc_id = payload.get("id") if isinstance(payload, dict) else None

        token = _bearer_token(scope)
        if token is None:
            await _reject(send, 401, rpc_id, "Unauthorized: bearer token required")
            return
        try:
            auth = await self.verifier(token)
        except Exception:
            logger.exception("Token verifier raised; rejecting the request")
            auth = None
        if auth is None:
            await _reject(send, 401, rpc_id, "Unauthorized: invalid token")
            return

        if isinstance(payload, dict) and payload.get("method") in _TASK_METHODS:
            denial = self._denial(payload, auth)
            if denial is not None:
                await _reject(send, 403, rpc_id, f"Forbidden: {denial}")
                return

        # The a2a-sdk turns these into the task owner and call-context state;
        # the executor reads the AuthContext back for current_auth().
        credentials, user = _starlette_auth_objects(auth)
        scope = {**scope, "auth": credentials, "user": user}
        await self.app(scope, replay_receive, send)

    def _denial(self, payload: dict[str, Any], auth: AuthContext) -> str | None:
        """Why a task request is forbidden for ``auth``, or ``None`` if allowed."""
        params = payload.get("params")
        params = params if isinstance(params, dict) else {}

        if self.require_task_scope:
            metadata = params.get("metadata")
            try:
                task_type = self.server._executor._resolve_task_type(
                    metadata if isinstance(metadata, dict) else None
                )
            except ValueError:
                task_type = None  # the executor fails the task: nothing to authorize
            if task_type is not None and not auth.allows(task_scope(task_type)):
                return f"token lacks scope {task_scope(task_type)}"

        if self._project_scoped():
            message = params.get("message")
            message = message if isinstance(message, dict) else {}
            project_id = _project_id(message)
            if project_id is None:
                # A follow-up message on an existing task (already authorized
                # and owner-scoped) may carry no data.
                if message.get("taskId"):
                    return None
                return "this agent is project-scoped; the request data needs a projectId"
            if not auth.allows(project_scope(project_id)):
                return f"token lacks scope {project_scope(project_id)}"
        return None

    def _project_scoped(self) -> bool:
        if self.require_project_scope is not None:
            return self.require_project_scope
        xc = self.server.agent_card.x_construction
        return bool(xc is not None and xc.security is not None and xc.security.project_scoped)


def _project_id(message: dict[str, Any]) -> str | None:
    """``projectId`` from the message's first data part (v0.3 or v1 wire shape)."""
    for part in message.get("parts") or []:
        data = part.get("data") if isinstance(part, dict) else None
        if isinstance(data, dict):
            project_id = data.get("projectId")
            return project_id if isinstance(project_id, str) and project_id else None
    return None


def _bearer_token(scope: Any) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == b"authorization":
            scheme, _, token = value.decode("latin-1").partition(" ")
            if scheme.lower() == "bearer" and token.strip():
                return token.strip()
            return None
    return None


async def _reject(send: Any, status: int, rpc_id: Any, message: str) -> None:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32000, "message": message}}
    ).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    if status == 401:
        headers.append((b"www-authenticate", b'Bearer realm="taco"'))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})

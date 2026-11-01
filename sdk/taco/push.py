"""Push-notification delivery for TACO agents.

The a2a-sdk only sends push notifications when its request handler is given
a sender; :class:`A2AServer` uses :class:`TacoPushNotificationSender` whenever
it has a push config store (the card advertises
``capabilities.push_notifications`` or a store is passed in).

Two things differ from the a2a-sdk's ``BasePushNotificationSender``:

- Whole numbers in the payload are sent as JSON integers, as in JSON-RPC
  responses (see :func:`taco.restore_integers`).
- Webhook URLs that resolve to loopback, private, link-local or other
  non-public addresses are refused by default. Any caller that can create a
  push config chooses the URL, so without this an agent could be made to
  POST to internal services or cloud metadata endpoints. Pass
  ``allow_private_urls=True`` (``A2AServer(allow_private_push_urls=True)``)
  for local development.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import urllib.parse
from typing import TYPE_CHECKING, Any

import httpx
from a2a.server.tasks.push_notification_sender import (
    PushNotificationEvent,
    PushNotificationSender,
)
from a2a.utils.proto_utils import to_stream_response
from google.protobuf.json_format import MessageToDict

from ._compat import restore_integers

if TYPE_CHECKING:
    from a2a.server.tasks import PushNotificationConfigStore
    from a2a.types.a2a_pb2 import TaskPushNotificationConfig

logger = logging.getLogger("taco.push")


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%", maxsplit=1)[0])
    except ValueError:
        return False
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped
    return addr.is_global and not (
        addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


async def is_public_http_url(url: str) -> bool:
    """Whether ``url`` is http(s) and every address its host resolves to is public."""
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, port, type=socket.SOCK_STREAM
        )
    except OSError:
        return False
    return bool(infos) and all(_is_public_ip(str(info[4][0])) for info in infos)


class TacoPushNotificationSender(PushNotificationSender):
    """Deliver push notifications to every webhook registered for a task.

    Delivery is best-effort: failures are logged and never fail the task.
    """

    def __init__(
        self,
        config_store: PushNotificationConfigStore,
        *,
        allow_private_urls: bool = False,
        timeout: float = 10.0,
    ) -> None:
        self._config_store = config_store
        self._allow_private_urls = allow_private_urls
        self._timeout = timeout

    async def send_notification(self, task_id: str, event: PushNotificationEvent) -> None:
        try:
            configs = await self._config_store.get_info_for_dispatch(task_id)
        except Exception:
            logger.exception("Could not read push configs for task %s", task_id)
            return
        if not configs:
            return
        payload = restore_integers(MessageToDict(to_stream_response(event)))
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await asyncio.gather(
                *(self._deliver(client, config, payload, task_id) for config in configs)
            )

    async def _deliver(
        self,
        client: httpx.AsyncClient,
        config: TaskPushNotificationConfig,
        payload: dict[str, Any],
        task_id: str,
    ) -> None:
        url = config.url
        if not self._allow_private_urls and not await is_public_http_url(url):
            logger.warning(
                "Not sending push notification for task %s: %s is not a public "
                "http(s) URL (A2AServer(allow_private_push_urls=True) allows it)",
                task_id,
                url,
            )
            return
        headers: dict[str, str] = {}
        if config.token:
            headers["X-A2A-Notification-Token"] = config.token
        if config.HasField("authentication"):
            auth = config.authentication
            if auth.scheme and auth.credentials:
                headers["Authorization"] = f"{auth.scheme} {auth.credentials}"
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except Exception:
            logger.exception("Push notification for task %s to %s failed", task_id, url)

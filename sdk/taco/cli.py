"""TACO CLI — command-line interface for interacting with TACO agents.

Usage::

    taco --version
    taco discover <url>
    taco inspect <url>
    taco send <url> <task_type> [json_file]
    taco health <url>
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .client import A2A_PROTOCOL_VERSION

_PROTOCOL_HEADERS = {"A2A-Version": A2A_PROTOCOL_VERSION}


def _get_http_client():
    try:
        import httpx
    except ImportError:
        print("httpx is required for the TACO CLI. Install with: pip install taco-agent[client]")
        sys.exit(1)
    return httpx


def _fetch_agent_card(httpx, url: str, timeout: float):
    """Fetch an agent card, preferring the A2A v0.3+ path.

    Tries ``/.well-known/agent-card.json`` first, falling back to the
    legacy ``/.well-known/agent.json`` on 404. Sends the
    ``A2A-Version`` header so v1 peers can negotiate.
    """
    resp = httpx.get(
        f"{url}/.well-known/agent-card.json",
        timeout=timeout,
        headers=_PROTOCOL_HEADERS,
    )
    if resp.status_code == 404:
        resp = httpx.get(
            f"{url}/.well-known/agent.json",
            timeout=timeout,
            headers=_PROTOCOL_HEADERS,
        )
    resp.raise_for_status()
    return resp


def _cmd_discover(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")
    resp = _fetch_agent_card(httpx, url, args.timeout)
    print(json.dumps(resp.json(), indent=2))


def _cmd_inspect(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")
    resp = _fetch_agent_card(httpx, url, args.timeout)
    card = resp.json()

    print(f"Agent: {card.get('name', 'Unknown')}")
    print(f"Description: {card.get('description', 'N/A')}")
    print(f"URL: {card.get('url', 'N/A')}")
    print(f"Version: {card.get('version', 'N/A')}")

    xc = card.get("x-construction")
    if xc:
        print("\nConstruction Extension:")
        print(f"  Trade: {xc.get('trade', 'N/A')}")
        divs = xc.get("csiDivisions", [])
        if divs:
            print(f"  CSI Divisions: {', '.join(divs)}")
        ptypes = xc.get("projectTypes", [])
        if ptypes:
            print(f"  Project Types: {', '.join(ptypes)}")

    skills = card.get("skills", [])
    if skills:
        print(f"\nSkills ({len(skills)}):")
        for s in skills:
            print(f"  - {s.get('name', s.get('id', 'Unknown'))}")
            if s.get("description"):
                print(f"    {s['description']}")
            sxc = s.get("x-construction")
            if sxc:
                print(f"    Task Type: {sxc.get('taskType', 'N/A')}")
                if sxc.get("inputSchema"):
                    print(f"    Input: {sxc['inputSchema']}")
                print(f"    Output: {sxc.get('outputSchema', 'N/A')}")


def _cmd_send(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")

    if args.json_file:
        with open(args.json_file) as f:
            input_data = json.load(f)
    elif not sys.stdin.isatty():
        input_data = json.load(sys.stdin)
    else:
        input_data = {}

    payload = {
        "jsonrpc": "2.0",
        "id": "cli-1",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "data", "data": input_data}],
                "messageId": "cli-msg-1",
            },
            "metadata": {"taskType": args.task_type},
        },
    }
    resp = httpx.post(
        f"{url}/",
        json=payload,
        timeout=args.timeout,
        headers=_PROTOCOL_HEADERS,
    )
    resp.raise_for_status()
    print(json.dumps(resp.json(), indent=2))


def _cmd_health(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")
    resp = httpx.get(f"{url}/health", timeout=args.timeout)
    resp.raise_for_status()
    data = resp.json()
    print(f"Status: {data.get('status', 'unknown')}")
    print(f"Agent: {data.get('agent', 'N/A')}")
    print(f"Version: {data.get('version', 'N/A')}")
    print(f"Uptime: {data.get('uptime_seconds', 'N/A')}s")
    handlers = data.get("handlers", [])
    if handlers:
        print(f"Handlers: {', '.join(handlers)}")


def _cmd_list_tasks(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")
    params: dict = {}
    if args.cursor:
        params["pageToken"] = args.cursor
    if args.limit:
        params["pageSize"] = args.limit
    if args.context_id:
        params["contextId"] = args.context_id

    payload = {
        "jsonrpc": "2.0",
        "id": "cli-1",
        "method": "ListTasks",
        "params": params,
    }
    # ListTasks is a v1-only method; override the default A2A-Version: 0.3.
    resp = httpx.post(
        f"{url}/",
        json=payload,
        timeout=args.timeout,
        headers={"A2A-Version": "1.0"},
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        err = body["error"]
        print(f"Error: {err.get('message', err)}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(body.get("result", {}), indent=2))
        return

    result = body.get("result", {})
    tasks = result.get("tasks", [])
    if not tasks:
        print("(no tasks)")
        return
    print(f"{len(tasks)} task(s):")
    for t in tasks:
        tid = t.get("id", "?")
        state = t.get("status", {}).get("state", "?")
        ctx = t.get("contextId", "")
        print(f"  - {tid}  state={state}  context={ctx}")
    next_token = result.get("nextPageToken")
    if next_token:
        print()
        print(f"Next page cursor: {next_token}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taco",
        description="TACO CLI — interact with TACO-compatible A2A agents",
    )
    parser.add_argument("--version", action="version", version=f"taco {__version__}")
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="HTTP timeout in seconds (default: 30)"
    )

    sub = parser.add_subparsers(dest="command")

    p_discover = sub.add_parser("discover", help="Fetch and print agent card as JSON")
    p_discover.add_argument("url", help="Agent base URL")

    p_inspect = sub.add_parser("inspect", help="Pretty-print agent details and skills")
    p_inspect.add_argument("url", help="Agent base URL")

    p_send = sub.add_parser("send", help="Send a task and print the result")
    p_send.add_argument("url", help="Agent base URL")
    p_send.add_argument("task_type", help="Task type to send")
    p_send.add_argument("json_file", nargs="?", default=None, help="JSON input file (or stdin)")

    p_health = sub.add_parser("health", help="Check agent /health endpoint")
    p_health.add_argument("url", help="Agent base URL")

    p_list = sub.add_parser("list-tasks", help="List tasks via the v1 ListTasks RPC")
    p_list.add_argument("url", help="Agent base URL")
    p_list.add_argument("--cursor", default=None, help="Pagination cursor from a previous call")
    p_list.add_argument(
        "--limit", type=int, default=None, help="Page size (server may apply its own cap)"
    )
    p_list.add_argument(
        "--context-id", default=None, help="Filter to tasks in this conversation context"
    )
    p_list.add_argument(
        "--json", action="store_true", help="Print the raw JSON-RPC result instead of a table"
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "discover": _cmd_discover,
        "inspect": _cmd_inspect,
        "send": _cmd_send,
        "health": _cmd_health,
        "list-tasks": _cmd_list_tasks,
    }
    try:
        commands[args.command](args)
    except Exception as exc:
        # If httpx raised an error, it's already imported in this process
        try:
            import httpx
        except ImportError:
            raise exc from None
        if isinstance(exc, httpx.HTTPStatusError):
            print(f"Error: HTTP {exc.response.status_code} from server", file=sys.stderr)
            sys.exit(1)
        elif isinstance(exc, httpx.ConnectError):
            print(f"Error: could not connect to server — {exc}", file=sys.stderr)
            sys.exit(1)
        else:
            raise


if __name__ == "__main__":
    main()

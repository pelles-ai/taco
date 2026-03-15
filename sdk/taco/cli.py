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


def _get_http_client():
    try:
        import httpx
    except ImportError:
        print("httpx is required for the TACO CLI. Install with: pip install taco-agent[client]")
        sys.exit(1)
    return httpx


def _cmd_discover(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")
    resp = httpx.get(f"{url}/.well-known/agent.json", timeout=args.timeout)
    resp.raise_for_status()
    print(json.dumps(resp.json(), indent=2))


def _cmd_inspect(args: argparse.Namespace) -> None:
    httpx = _get_http_client()
    url = args.url.rstrip("/")
    resp = httpx.get(f"{url}/.well-known/agent.json", timeout=args.timeout)
    resp.raise_for_status()
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
    resp = httpx.post(f"{url}/", json=payload, timeout=args.timeout)
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

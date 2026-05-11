"""Tests for taco.cli — CLI tool."""

from __future__ import annotations

import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from taco import __version__
from taco.cli import build_parser, main


class TestParserSetup:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_no_args_prints_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "taco" in captured.out.lower()

    def test_parser_has_subcommands(self):
        parser = build_parser()
        # Verify parser can parse known subcommands without error
        args = parser.parse_args(["discover", "http://localhost:8001"])
        assert args.command == "discover"
        assert args.url == "http://localhost:8001"

    def test_parser_send_with_file(self):
        parser = build_parser()
        args = parser.parse_args(["send", "http://localhost:8001", "estimate", "input.json"])
        assert args.command == "send"
        assert args.task_type == "estimate"
        assert args.json_file == "input.json"

    def test_parser_send_without_file(self):
        parser = build_parser()
        args = parser.parse_args(["send", "http://localhost:8001", "estimate"])
        assert args.command == "send"
        assert args.json_file is None


class TestDiscoverCommand:
    @patch("taco.cli._get_http_client")
    def test_discover_prints_json(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"name": "Test Agent", "url": "http://localhost:8001"}
        mock_httpx.get.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["discover", "http://localhost:8001"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["name"] == "Test Agent"


class TestInspectCommand:
    @patch("taco.cli._get_http_client")
    def test_inspect_prints_details(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "name": "Test Agent",
            "description": "A test agent",
            "url": "http://localhost:8001",
            "version": "1.0.0",
            "x-construction": {
                "trade": "mechanical",
                "csiDivisions": ["23"],
                "projectTypes": ["commercial"],
            },
            "skills": [
                {
                    "id": "est",
                    "name": "Estimate",
                    "description": "Generate estimate",
                    "x-construction": {
                        "taskType": "estimate",
                        "outputSchema": "estimate-v1",
                    },
                },
            ],
        }
        mock_httpx.get.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["inspect", "http://localhost:8001"])
        captured = capsys.readouterr()
        assert "Test Agent" in captured.out
        assert "mechanical" in captured.out
        assert "Estimate" in captured.out


class TestHealthCommand:
    @patch("taco.cli._get_http_client")
    def test_health_prints_status(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "ok",
            "agent": "Test Agent",
            "version": "0.3.0",
            "uptime_seconds": 42.5,
            "handlers": ["estimate"],
        }
        mock_httpx.get.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["health", "http://localhost:8001"])
        captured = capsys.readouterr()
        assert "ok" in captured.out
        assert "Test Agent" in captured.out
        assert "estimate" in captured.out


class TestListTasksCommand:
    @patch("taco.cli._get_http_client")
    def test_list_tasks_prints_table(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "cli-1",
            "result": {
                "tasks": [
                    {"id": "t-1", "contextId": "c-1", "status": {"state": "completed"}},
                    {"id": "t-2", "contextId": "c-1", "status": {"state": "working"}},
                ],
                "nextPageToken": "cursor-xyz",
            },
        }
        mock_httpx.post.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["list-tasks", "http://localhost:8001", "--limit", "2"])

        captured = capsys.readouterr()
        assert "t-1" in captured.out
        assert "completed" in captured.out
        assert "t-2" in captured.out
        assert "Next page cursor: cursor-xyz" in captured.out

        # Verify the v1 ListTasks method and v1 header were used
        call_args = mock_httpx.post.call_args
        assert call_args[1]["json"]["method"] == "ListTasks"
        assert call_args[1]["json"]["params"]["pageSize"] == 2
        assert call_args[1]["headers"]["A2A-Version"] == "1.0"

    @patch("taco.cli._get_http_client")
    def test_list_tasks_handles_empty(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "cli-1",
            "result": {"tasks": []},
        }
        mock_httpx.post.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["list-tasks", "http://localhost:8001"])

        captured = capsys.readouterr()
        assert "(no tasks)" in captured.out

    @patch("taco.cli._get_http_client")
    def test_list_tasks_json_flag(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "cli-1",
            "result": {"tasks": [{"id": "t-1"}]},
        }
        mock_httpx.post.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["list-tasks", "http://localhost:8001", "--json"])

        captured = capsys.readouterr()
        # --json prints the raw RPC result; should be valid JSON
        parsed = json.loads(captured.out)
        assert parsed["tasks"][0]["id"] == "t-1"


class TestSendCommand:
    @patch("taco.cli._get_http_client")
    def test_send_with_empty_input(self, mock_get_client, capsys):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "cli-1",
            "result": {"status": {"state": "completed"}},
        }
        mock_httpx.post.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        # Simulate tty to avoid reading stdin
        with patch("taco.cli.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            mock_sys.exit = SystemExit
            from types import SimpleNamespace

            # Re-import to get patched sys
            from taco.cli import _cmd_send

            args = SimpleNamespace(
                url="http://localhost:8001",
                task_type="estimate",
                json_file=None,
                timeout=30.0,
            )
            _cmd_send(args)

        captured = capsys.readouterr()
        assert "completed" in captured.out

    @patch("taco.cli._get_http_client")
    def test_send_with_json_file(self, mock_get_client, capsys, tmp_path):
        input_data = {"projectId": "PRJ-001", "trade": "mechanical"}
        json_file = tmp_path / "input.json"
        json_file.write_text(json.dumps(input_data))

        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "cli-1",
            "result": {"status": {"state": "completed"}},
        }
        mock_httpx.post.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        main(["send", "http://localhost:8001", "estimate", str(json_file)])

        # Verify input_data was sent in the payload
        call_args = mock_httpx.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["message"]["parts"][0]["data"] == input_data

        captured = capsys.readouterr()
        assert "completed" in captured.out

    @patch("taco.cli._get_http_client")
    def test_send_with_stdin(self, mock_get_client, capsys):
        input_data = {"projectId": "PRJ-002"}

        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "cli-1",
            "result": {"status": {"state": "completed"}},
        }
        mock_httpx.post.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        fake_stdin = StringIO(json.dumps(input_data))
        fake_stdin.isatty = lambda: False

        with patch.object(sys, "stdin", fake_stdin):
            main(["send", "http://localhost:8001", "estimate"])

        call_args = mock_httpx.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["message"]["parts"][0]["data"] == input_data


class TestCLIErrorHandling:
    @patch("taco.cli._get_http_client")
    def test_http_status_error(self, mock_get_client, capsys):
        import httpx as real_httpx

        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = real_httpx.HTTPStatusError(
            "Server Error",
            request=real_httpx.Request("GET", "http://localhost:8001/health"),
            response=real_httpx.Response(500),
        )
        mock_httpx.get.return_value = mock_resp
        mock_get_client.return_value = mock_httpx

        with pytest.raises(SystemExit) as exc_info:
            main(["health", "http://localhost:8001"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "HTTP 500" in captured.err

    @patch("taco.cli._get_http_client")
    def test_connect_error(self, mock_get_client, capsys):
        import httpx as real_httpx

        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = real_httpx.ConnectError("Connection refused")
        mock_get_client.return_value = mock_httpx

        with pytest.raises(SystemExit) as exc_info:
            main(["health", "http://localhost:8001"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "could not connect" in captured.err

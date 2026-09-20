"""Tests for MCP JSON-RPC behavior."""

from pathlib import Path

from ai_collaboration.config import Settings
from ai_collaboration.mcp_server import MCPServer
from ai_collaboration.service import CollaborationService
from ai_collaboration.storage import EventStore


def server(tmp_path: Path) -> MCPServer:
    settings = Settings(home=tmp_path, database=tmp_path / "state.db", objects=tmp_path / "objects")
    return MCPServer(CollaborationService(EventStore(settings)))


def test_initialize_echoes_protocol_and_server_info(tmp_path: Path) -> None:
    result = server(tmp_path).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )
    assert result["result"]["protocolVersion"] == "2025-06-18"
    assert result["result"]["serverInfo"]["name"] == "ai-collaboration"


def test_initialize_falls_back_for_unsupported_protocol(tmp_path: Path) -> None:
    result = server(tmp_path).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2099-01-01"},
        }
    )

    assert result["result"]["protocolVersion"] == "2025-06-18"


def test_tools_list_contains_continuity_api(tmp_path: Path) -> None:
    result = server(tmp_path).handle(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    names = {tool["name"] for tool in result["result"]["tools"]}
    assert {
        "ai_collaboration.get_context",
        "ai_collaboration.search_history",
        "ai_collaboration.record_checkpoint",
        "ai_collaboration.changed_files",
    }.issubset(names)


def test_tools_call_returns_structured_and_text_content(tmp_path: Path) -> None:
    app = server(tmp_path)
    result = app.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "ai_collaboration.start_task",
                "arguments": {"title": "MCP task", "cwd": str(tmp_path)},
            },
        }
    )
    assert result["result"]["isError"] is False
    assert result["result"]["structuredContent"]["result"]["title"] == "MCP task"
    assert "MCP task" in result["result"]["content"][0]["text"]


def test_unknown_method_and_tool_are_json_rpc_errors(tmp_path: Path) -> None:
    app = server(tmp_path)
    method = app.handle({"jsonrpc": "2.0", "id": 4, "method": "missing"})
    tool = app.handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "missing", "arguments": {}},
        }
    )
    assert method["error"]["code"] == -32601
    assert tool["error"]["code"] == -32602


def test_unexpected_errors_do_not_disclose_details(tmp_path: Path, capsys) -> None:
    app = server(tmp_path)

    def fail(_values):
        raise RuntimeError("private/path/secret")

    app.tools["ai_collaboration.status"]["handler"] = fail
    result = app.handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "ai_collaboration.status", "arguments": {}},
        }
    )

    assert result["error"] == {"code": -32603, "message": "Internal error"}
    assert capsys.readouterr().err.strip() == "MCP handler failed: RuntimeError"


def test_notifications_do_not_produce_responses(tmp_path: Path) -> None:
    assert (
        server(tmp_path).handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    )

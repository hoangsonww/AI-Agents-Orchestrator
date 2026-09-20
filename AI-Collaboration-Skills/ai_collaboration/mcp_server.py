"""Minimal dependency-free MCP stdio server."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from . import __version__
from .service import CollaborationService

ToolHandler = Callable[[Mapping[str, Any]], Any]
SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[-1]


class MCPServer:
    """Serve AI Collaboration tools over newline-delimited JSON-RPC."""

    def __init__(self, service: Optional[CollaborationService] = None) -> None:
        self.service = service or CollaborationService()
        self.tools = self._tools()

    def _tools(self) -> Dict[str, Dict[str, Any]]:
        string = {"type": "string"}
        cwd = {
            "cwd": {
                **string,
                "description": "Repository path; defaults to the host working directory.",
            }
        }
        return {
            "ai_collaboration.current_task": self._tool(
                "Get the active continuity task for a repository.",
                {"type": "object", "properties": cwd, "additionalProperties": False},
                lambda values: self.service.current_task(values.get("cwd")),
            ),
            "ai_collaboration.status": self._tool(
                "Get task, session, checkpoint, recent-event, and Git status.",
                {"type": "object", "properties": cwd, "additionalProperties": False},
                lambda values: self.service.status(values.get("cwd")),
            ),
            "ai_collaboration.sessions": self._tool(
                "List agent sessions attached to a task.",
                {
                    "type": "object",
                    "properties": {
                        "task_id": string,
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    },
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
                lambda values: self.service.store.list_sessions(
                    values["task_id"], values.get("limit", 50)
                ),
            ),
            "ai_collaboration.search_history": self._tool(
                "Search captured commands and event summaries for the current or specified task.",
                {
                    "type": "object",
                    "properties": {
                        "query": string,
                        "task_id": string,
                        **cwd,
                        "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                lambda values: self.service.search(
                    values["query"],
                    values.get("cwd"),
                    values.get("task_id"),
                    values.get("limit", 50),
                ),
            ),
            "ai_collaboration.session_events": self._tool(
                "List normalized events for a session, optionally including redacted raw payloads.",
                {
                    "type": "object",
                    "properties": {
                        "session_id": string,
                        "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                        "include_payload": {"type": "boolean"},
                    },
                    "required": ["session_id"],
                    "additionalProperties": False,
                },
                lambda values: self.service.store.list_events(
                    session_id=values["session_id"],
                    limit=values.get("limit", 100),
                    include_payload=values.get("include_payload", False),
                ),
            ),
            "ai_collaboration.changed_files": self._tool(
                "Inspect current Git branch, head, and changed files.",
                {"type": "object", "properties": cwd, "additionalProperties": False},
                lambda values: self.service.changed_files(values.get("cwd")),
            ),
            "ai_collaboration.test_history": self._tool(
                "List captured test commands and outcomes for a task.",
                {
                    "type": "object",
                    "properties": {
                        "task_id": string,
                        "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    },
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
                lambda values: self.service.test_history(
                    values["task_id"], values.get("limit", 25)
                ),
            ),
            "ai_collaboration.get_context": self._tool(
                "Build deterministic handoff context from current task, Git, sessions, tests, files, and checkpoint.",
                {
                    "type": "object",
                    "properties": {
                        **cwd,
                        "event_limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    },
                    "additionalProperties": False,
                },
                lambda values: self.service.context(
                    values.get("cwd"), values.get("event_limit", 25)
                ),
            ),
            "ai_collaboration.record_checkpoint": self._tool(
                "Record an intentional handoff checkpoint and suggested next action.",
                {
                    "type": "object",
                    "properties": {
                        "summary": string,
                        "next_action": string,
                        "provider": string,
                        "task_id": string,
                        "session_id": string,
                        **cwd,
                    },
                    "required": ["summary"],
                    "additionalProperties": False,
                },
                lambda values: self.service.checkpoint(
                    values["summary"],
                    values.get("next_action", ""),
                    values.get("provider", "mcp"),
                    values.get("cwd"),
                    values.get("task_id"),
                    values.get("session_id"),
                ),
            ),
            "ai_collaboration.start_task": self._tool(
                "Start and activate a named continuity task for a repository.",
                {
                    "type": "object",
                    "properties": {"title": string, "description": string, **cwd},
                    "required": ["title"],
                    "additionalProperties": False,
                },
                lambda values: self.service.start_task(
                    values["title"], values.get("cwd"), values.get("description", "")
                ),
            ),
        }

    @staticmethod
    def _tool(description: str, schema: Dict[str, Any], handler: ToolHandler) -> Dict[str, Any]:
        return {"description": description, "inputSchema": schema, "handler": handler}

    def handle(self, message: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method")
        request_id = message.get("id")
        if request_id is None:
            return None
        try:
            if method == "initialize":
                requested = message.get("params", {}).get(
                    "protocolVersion", LATEST_PROTOCOL_VERSION
                )
                negotiated = (
                    requested
                    if requested in SUPPORTED_PROTOCOL_VERSIONS
                    else LATEST_PROTOCOL_VERSION
                )
                result = {
                    "protocolVersion": negotiated,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "ai-collaboration", "version": __version__},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": name,
                            "description": spec["description"],
                            "inputSchema": spec["inputSchema"],
                        }
                        for name, spec in self.tools.items()
                    ]
                }
            elif method == "tools/call":
                parameters = message.get("params", {})
                name = parameters.get("name")
                if name not in self.tools:
                    raise KeyError("unknown tool: %s" % name)
                arguments = parameters.get("arguments") or {}
                value = self.tools[name]["handler"](arguments)
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                value, ensure_ascii=False, indent=2, sort_keys=True, default=str
                            ),
                        }
                    ],
                    "structuredContent": {"result": value},
                    "isError": False,
                }
            else:
                return self._error(request_id, -32601, "Method not found: %s" % method)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except (KeyError, ValueError) as error:
            return self._error(request_id, -32602, str(error))
        except Exception as error:  # Keep protocol output valid; diagnostics stay on stderr.
            print("MCP handler failed: %s" % type(error).__name__, file=sys.stderr)
            return self._error(request_id, -32603, "Internal error")

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def serve(self) -> int:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = self.handle(message)
            except json.JSONDecodeError as error:
                response = self._error(None, -32700, "Parse error: %s" % error)
            if response is not None:
                sys.stdout.write(json.dumps(response, separators=(",", ":"), default=str) + "\n")
                sys.stdout.flush()
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    del argv
    return MCPServer().serve()


if __name__ == "__main__":
    raise SystemExit(main())

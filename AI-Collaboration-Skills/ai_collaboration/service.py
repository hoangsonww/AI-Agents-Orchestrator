"""Application service for normalized continuity operations."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .config import Settings
from .git_state import repository_root, snapshot
from .security import redact, unique_strings
from .storage import EventStore, utc_now

_TEST_COMMAND = re.compile(
    r"(?:^|\s)(?:pytest|python\s+-m\s+pytest|npm\s+(?:run\s+)?test|pnpm\s+(?:run\s+)?test|"
    r"yarn\s+test|cargo\s+test|go\s+test|dotnet\s+test|mvn\s+test|gradle\s+test)(?:\s|$)",
    re.IGNORECASE,
)


class CollaborationService:
    """Coordinate task, session, event, and context behavior."""

    def __init__(self, store: Optional[EventStore] = None) -> None:
        self.store = store or EventStore()

    @classmethod
    def from_home(cls, home: Optional[Path] = None) -> "CollaborationService":
        return cls(EventStore(Settings.load(home)))

    def repo(self, cwd: Optional[str] = None) -> Path:
        return repository_root(Path(cwd or os.getcwd()))

    def start_task(
        self, title: str, cwd: Optional[str] = None, description: str = ""
    ) -> Dict[str, Any]:
        if not title.strip():
            raise ValueError("task title must not be empty")
        return self.store.create_task(title.strip(), str(self.repo(cwd)), description.strip())

    def current_task(
        self, cwd: Optional[str] = None, create: bool = False
    ) -> Optional[Dict[str, Any]]:
        root = self.repo(cwd)
        task = self.store.current_task(str(root))
        if task or not create:
            return task
        return self.store.create_task("Continue work in %s" % root.name, str(root))

    def ingest(self, provider: str, event_type: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Normalize one provider hook payload and persist it."""

        safe_payload = redact(dict(payload))
        cwd = str(
            payload.get("cwd")
            or payload.get("workspacePath")
            or payload.get("workspace_path")
            or os.getcwd()
        )
        root = self.repo(cwd)
        task = self.current_task(str(root), create=True)
        if not task:
            raise RuntimeError("could not resolve an active task")
        session_id = self._session_id(provider, payload, root)
        self.store.ensure_session(
            session_id,
            task["id"],
            provider,
            cwd,
            {"source_event": event_type},
        )
        git = snapshot(root)
        tool = self._first(safe_payload, "tool_name", "toolName", "tool", "name")
        tool_input = self._first(
            safe_payload, "tool_input", "toolInput", "tool_args", "toolArgs", default={}
        )
        command = self._command(tool_input, safe_payload)
        files_read, files_written = self._files(
            event_type, str(tool or ""), tool_input, safe_payload
        )
        exit_code = self._exit_code(payload)
        summary = self._summary(event_type, tool, command, exit_code, safe_payload)
        normalized = {
            "task_id": task["id"],
            "session_id": session_id,
            "provider": provider,
            "timestamp": self._timestamp(payload),
            "event_type": event_type,
            "tool": tool,
            "command": command,
            "exit_code": exit_code,
            "cwd": cwd,
            "git_head": git.get("head"),
            "git_branch": git.get("branch"),
            "files_read": files_read,
            "files_written": files_written,
            "summary": summary,
        }
        event = self.store.add_event(normalized, safe_payload)
        if event_type.lower() in {"sessionend", "session_end"}:
            self.store.end_session(session_id)
        return event

    def status(self, cwd: Optional[str] = None) -> Dict[str, Any]:
        root = self.repo(cwd)
        task = self.store.current_task(str(root))
        git = snapshot(root)
        if not task:
            return {"repository": git, "task": None, "sessions": [], "recent_events": []}
        return {
            "repository": git,
            "task": task,
            "sessions": self.store.list_sessions(task["id"], limit=10),
            "recent_events": self.store.list_events(task_id=task["id"], limit=10),
            "checkpoint": self.store.latest_checkpoint(task["id"]),
        }

    def context(self, cwd: Optional[str] = None, event_limit: int = 25) -> Dict[str, Any]:
        state = self.status(cwd)
        task = state.get("task")
        if not task:
            state["suggested_next_action"] = (
                "Start a task with ai-collaboration task start <title>."
            )
            return state
        events = self.store.list_events(task_id=task["id"], limit=event_limit)
        recent_files = unique_strings(
            path
            for event in events
            for path in event.get("files_written", []) + event.get("files_read", [])
        )[:20]
        tests = self.test_history(task["id"], limit=10)
        checkpoint = self.store.latest_checkpoint(task["id"])
        next_action = "Inspect the current git diff and the most recent events."
        if checkpoint and checkpoint.get("next_action"):
            next_action = checkpoint["next_action"]
        elif tests and tests[0].get("exit_code") not in (None, 0):
            next_action = "Reproduce and diagnose the most recent failing test command."
        state.update(
            {
                "recent_events": events,
                "recent_files": recent_files,
                "test_history": tests,
                "suggested_next_action": next_action,
            }
        )
        return state

    def search(
        self, query: str, cwd: Optional[str] = None, task_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        if not query.strip():
            raise ValueError("search query must not be empty")
        if not task_id:
            task = self.current_task(cwd)
            task_id = task["id"] if task else None
        return self.store.search(query.strip(), task_id=task_id, limit=limit)

    def changed_files(self, cwd: Optional[str] = None) -> Dict[str, Any]:
        return snapshot(self.repo(cwd))

    def test_history(self, task_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        events = self.store.list_events(task_id=task_id, limit=1000)
        return [
            event
            for event in events
            if event.get("command") and _TEST_COMMAND.search(event["command"])
        ][:limit]

    def checkpoint(
        self,
        summary: str,
        next_action: str = "",
        provider: str = "manual",
        cwd: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not summary.strip():
            raise ValueError("checkpoint summary must not be empty")
        if not task_id:
            task = self.current_task(cwd)
            if not task:
                raise ValueError("no active task; start or select one first")
            task_id = task["id"]
        return self.store.add_checkpoint(
            task_id,
            provider,
            summary.strip(),
            next_action.strip(),
            session_id=session_id,
            metadata={"repository": str(self.repo(cwd))},
        )

    @staticmethod
    def _first(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        return default

    def _session_id(self, provider: str, payload: Mapping[str, Any], root: Path) -> str:
        supplied = self._first(
            payload, "session_id", "sessionId", "conversation_id", "conversationId"
        )
        if supplied:
            return "%s:%s" % (provider, supplied)
        seed = "%s\x00%s\x00%s" % (provider, root, os.getppid())
        return "%s:auto-%s" % (provider, hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20])

    @staticmethod
    def _timestamp(payload: Mapping[str, Any]) -> str:
        value = payload.get("timestamp")
        if isinstance(value, (int, float)):
            from datetime import datetime, timezone

            return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).isoformat()
        return str(value) if value else utc_now()

    @staticmethod
    def _command(tool_input: Any, payload: Mapping[str, Any]) -> Optional[str]:
        if isinstance(tool_input, Mapping):
            for key in ("command", "cmd", "script"):
                if tool_input.get(key):
                    return str(tool_input[key])[:20000]
        for key in ("command", "cmd"):
            if payload.get(key):
                return str(payload[key])[:20000]
        return None

    @staticmethod
    def _files(
        event_type: str, tool: str, tool_input: Any, payload: Mapping[str, Any]
    ) -> Tuple[List[str], List[str]]:
        candidates: List[Any] = []
        if isinstance(tool_input, Mapping):
            for key in ("file_path", "filePath", "path", "paths", "files"):
                value = tool_input.get(key)
                if isinstance(value, list):
                    candidates.extend(value)
                elif value:
                    candidates.append(value)
        for key in ("file_path", "filePath", "path"):
            if payload.get(key):
                candidates.append(payload[key])
        files = unique_strings(candidates)
        label = (event_type + " " + tool).lower()
        if any(word in label for word in ("write", "edit", "patch", "create", "fileedit")):
            return [], files
        if any(word in label for word in ("read", "view", "grep", "glob")):
            return files, []
        return [], []

    @staticmethod
    def _exit_code(payload: Mapping[str, Any]) -> Optional[int]:
        values: Sequence[Any] = (
            payload.get("exit_code"),
            payload.get("exitCode"),
            (
                payload.get("tool_response", {}).get("exit_code")
                if isinstance(payload.get("tool_response"), Mapping)
                else None
            ),
            (
                payload.get("toolResult", {}).get("exitCode")
                if isinstance(payload.get("toolResult"), Mapping)
                else None
            ),
        )
        for value in values:
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _summary(
        event_type: str,
        tool: Any,
        command: Optional[str],
        exit_code: Optional[int],
        payload: Mapping[str, Any],
    ) -> str:
        prompt = (
            payload.get("prompt") or payload.get("initial_prompt") or payload.get("initialPrompt")
        )
        if prompt:
            return "%s: %s" % (event_type, str(prompt)[:1000])
        parts = [event_type]
        if tool:
            parts.append(str(tool))
        if command:
            parts.append(command[:1000])
        if exit_code is not None:
            parts.append("exit=%s" % exit_code)
        error = payload.get("error")
        if error:
            parts.append(str(error)[:1000])
        return " | ".join(parts)

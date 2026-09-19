"""Tests for SQLite and object persistence."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ai_collaboration.config import Settings
from ai_collaboration.storage import EventStore


def make_store(tmp_path: Path, inline: int = 128) -> EventStore:
    settings = Settings(
        home=tmp_path,
        database=tmp_path / "state.db",
        objects=tmp_path / "objects",
        inline_payload_bytes=inline,
    )
    return EventStore(settings)


def event(task_id: str, session_id: str, summary: str = "edited ownership validation") -> dict:
    return {
        "task_id": task_id,
        "session_id": session_id,
        "provider": "claude",
        "event_type": "PostToolUse",
        "tool": "Edit",
        "cwd": "/repo",
        "files_written": ["src/session.py"],
        "summary": summary,
    }


def test_task_lifecycle_and_repo_activation(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = store.create_task("First", "/repo")
    second = store.create_task("Second", "/repo")

    assert store.current_task("/repo")["id"] == second["id"]
    store.activate_task(first["id"])
    assert store.current_task("/repo")["id"] == first["id"]
    completed = store.complete_task(first["id"])
    assert completed["status"] == "completed"
    assert store.current_task("/repo") is None


def test_large_payload_uses_content_addressed_object(tmp_path: Path) -> None:
    store = make_store(tmp_path, inline=32)
    task = store.create_task("Task", "/repo")
    store.ensure_session("claude:1", task["id"], "claude", "/repo")

    saved = store.add_event(event(task["id"], "claude:1"), {"output": "x" * 500})

    assert saved["payload_ref"]
    object_files = list((tmp_path / "objects").rglob("*.json.gz"))
    assert len(object_files) == 1
    loaded = store.get_event(saved["id"], include_payload=True)
    assert loaded["payload"]["output"] == "x" * 500


def test_inline_payload_and_search(tmp_path: Path) -> None:
    store = make_store(tmp_path, inline=4096)
    task = store.create_task("Task", "/repo")
    store.ensure_session("claude:1", task["id"], "claude", "/repo")
    saved = store.add_event(event(task["id"], "claude:1"), {"small": True})

    assert saved["payload_ref"] is None
    assert store.get_event(saved["id"], include_payload=True)["payload"] == {"small": True}
    assert store.search("ownership", task["id"])[0]["id"] == saved["id"]


def test_sessions_checkpoints_and_stats(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    task = store.create_task("Task", "/repo")
    store.ensure_session("codex:1", task["id"], "codex", "/repo")
    store.add_event(event(task["id"], "codex:1"), {})
    checkpoint = store.add_checkpoint(
        task["id"], "codex", "Implemented core", "Run tests", "codex:1"
    )
    store.end_session("codex:1")

    sessions = store.list_sessions(task["id"])
    assert sessions[0]["event_count"] == 1
    assert sessions[0]["ended_at"] is not None
    assert store.latest_checkpoint(task["id"])["id"] == checkpoint["id"]
    assert store.stats()["events"] == 1


def test_concurrent_event_writes(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    task = store.create_task("Task", "/repo")

    def write(index: int) -> None:
        session_id = "agent:%s" % index
        store.ensure_session(session_id, task["id"], "agent", "/repo")
        store.add_event(event(task["id"], session_id, "event %s" % index), {"index": index})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(24)))

    assert len(store.list_events(task_id=task["id"], limit=100)) == 24

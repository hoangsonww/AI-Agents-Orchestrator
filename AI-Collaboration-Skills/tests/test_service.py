"""Tests for event normalization and context assembly."""

import subprocess
from pathlib import Path

from ai_collaboration.config import Settings
from ai_collaboration.service import CollaborationService
from ai_collaboration.storage import EventStore


def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "initial"], check=True)
    return tmp_path


def service(tmp_path: Path) -> CollaborationService:
    home = tmp_path / "data"
    settings = Settings(home=home, database=home / "state.db", objects=home / "objects")
    return CollaborationService(EventStore(settings))


def test_ingest_creates_task_and_normalizes_claude_event(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    app = service(tmp_path)
    result = app.ingest(
        "claude",
        "PostToolUse",
        {
            "session_id": "abc",
            "cwd": str(repo),
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/app.py"},
            "api_token": "secret",
        },
    )

    assert result["provider"] == "claude"
    assert result["session_id"] == "claude:abc"
    assert result["files_written"] == ["src/app.py"]
    loaded = app.store.get_event(result["id"], include_payload=True)
    assert loaded["payload"]["api_token"] == "[REDACTED]"
    assert app.current_task(str(repo))["title"] == "Continue work in repo"


def test_ingest_redacts_normalized_command_and_summary(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    app = service(tmp_path)
    result = app.ingest(
        "claude",
        "PostToolUse",
        {
            "cwd": str(repo),
            "session_id": "secret-regression",
            "tool_name": "Bash",
            "tool_input": {
                "command": "curl -H 'Authorization: Bearer secret-token-value' example.test"
            },
        },
    )

    assert "secret-token-value" not in result["command"]
    assert "secret-token-value" not in result["summary"]
    assert "[REDACTED]" in result["command"]


def test_ingest_redacts_file_metadata(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    app = service(tmp_path)
    result = app.ingest(
        "claude",
        "Read",
        {
            "cwd": str(repo),
            "session_id": "path-secret-regression",
            "tool_name": "Read",
            "file_path": "token=secret-token-value",
        },
    )

    assert result["files_read"] == ["token=[REDACTED]"]


def test_provider_field_variants_and_test_history(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    app = service(tmp_path)
    app.start_task("Fix tests", str(repo))
    app.ingest(
        "cursor",
        "postToolUse",
        {
            "sessionId": "cursor-1",
            "cwd": str(repo),
            "toolName": "Shell",
            "toolArgs": {"command": "python -m pytest tests -q"},
            "exitCode": 1,
        },
    )

    context = app.context(str(repo))
    assert context["test_history"][0]["exit_code"] == 1
    assert "failing test" in context["suggested_next_action"]


def test_checkpoint_takes_priority_for_next_action(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    app = service(tmp_path)
    task = app.start_task("Feature", str(repo))
    app.checkpoint("Core done", "Add adapter tests", "codex", str(repo), task["id"])

    assert app.context(str(repo))["suggested_next_action"] == "Add adapter tests"


def test_changed_files_reads_current_tree(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    app = service(tmp_path)

    changed = app.changed_files(str(repo))["changed_files"]

    assert changed == [{"status": " M", "path": "README.md"}]


def test_changed_files_preserves_rename_destination(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    subprocess.run(["git", "-C", str(repo), "mv", "README.md", "RENAMED.md"], check=True)
    app = service(tmp_path)

    assert app.changed_files(str(repo))["changed_files"] == [
        {"status": "R ", "path": "RENAMED.md", "previous_path": "README.md"}
    ]

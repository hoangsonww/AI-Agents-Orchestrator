"""Black-box tests for packaged executable entry points."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(home: Path, *args: str, input_text: str = "") -> subprocess.CompletedProcess:
    environment = {**os.environ, "AI_COLLABORATION_HOME": str(home)}
    return subprocess.run(
        [str(ROOT / "bin" / "ai-collaboration"), *args],
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        env=environment,
    )


def test_cli_task_status_and_checkpoint(tmp_path: Path) -> None:
    started = run_cli(tmp_path / "data", "task", "start", "CLI task", "--cwd", str(tmp_path))
    task = json.loads(started.stdout)
    assert started.returncode == 0
    assert task["title"] == "CLI task"

    checkpoint = run_cli(
        tmp_path / "data",
        "checkpoint",
        "Core implemented",
        "--next-action",
        "Run tests",
        "--cwd",
        str(tmp_path),
    )
    assert json.loads(checkpoint.stdout)["next_action"] == "Run tests"
    assert (
        json.loads(run_cli(tmp_path / "data", "status", "--cwd", str(tmp_path)).stdout)["task"][
            "id"
        ]
        == task["id"]
    )


def test_cli_returns_error_for_empty_search(tmp_path: Path) -> None:
    result = run_cli(tmp_path / "data", "search", "")
    assert result.returncode == 2
    assert "must not be empty" in result.stderr


def test_cli_events_defaults_to_active_task(tmp_path: Path) -> None:
    home = tmp_path / "data"
    first = json.loads(run_cli(home, "task", "start", "First", "--cwd", str(tmp_path)).stdout)
    run_cli(
        home,
        "ingest",
        "--provider",
        "test",
        "--event",
        "Prompt",
        input_text=json.dumps(
            {"cwd": str(tmp_path), "session_id": "first", "prompt": "first task"}
        ),
    )
    second = json.loads(run_cli(home, "task", "start", "Second", "--cwd", str(tmp_path)).stdout)
    run_cli(
        home,
        "ingest",
        "--provider",
        "test",
        "--event",
        "Prompt",
        input_text=json.dumps(
            {"cwd": str(tmp_path), "session_id": "second", "prompt": "second task"}
        ),
    )

    events = json.loads(run_cli(home, "events", "--cwd", str(tmp_path)).stdout)

    assert first["id"] != second["id"]
    assert {event["task_id"] for event in events} == {second["id"]}


def test_hook_is_fail_open_for_invalid_json(tmp_path: Path) -> None:
    environment = {**os.environ, "AI_COLLABORATION_HOME": str(tmp_path / "data")}
    result = subprocess.run(
        ["python3", str(ROOT / "hooks" / "ingest.py"), "--provider", "test", "--event", "Broken"],
        input="not json",
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {}
    assert result.stderr.strip() == "AI Collaboration capture skipped."

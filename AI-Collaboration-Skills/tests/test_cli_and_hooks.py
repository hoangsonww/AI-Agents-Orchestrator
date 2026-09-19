"""Black-box tests for packaged executable entry points."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(home: Path, *args: str) -> subprocess.CompletedProcess:
    environment = {**os.environ, "AI_COLLABORATION_HOME": str(home)}
    return subprocess.run(
        [str(ROOT / "bin" / "ai-collaboration"), *args],
        check=False,
        capture_output=True,
        text=True,
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
    assert "capture skipped" in result.stderr

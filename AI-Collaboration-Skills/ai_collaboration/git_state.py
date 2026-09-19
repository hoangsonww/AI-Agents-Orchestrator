"""Read-only repository state capture."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def repository_root(cwd: Path) -> Path:
    """Return the containing Git repository or the resolved working directory."""

    output = _git(cwd, "rev-parse", "--show-toplevel")
    return Path(output).resolve() if output else cwd.resolve()


def snapshot(cwd: Path) -> Dict[str, object]:
    """Capture branch, head, and working-tree changes without mutating Git state."""

    root = repository_root(cwd)
    status = _git(root, "status", "--porcelain=v1", "-z")
    changed: List[Dict[str, str]] = []
    if status:
        entries = status.split("\x00")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if not entry:
                continue
            code = entry[:2]
            path = entry[3:] if len(entry) > 3 else ""
            if code[:1] in {"R", "C"} and index < len(entries):
                destination = entries[index]
                index += 1
                changed.append({"status": code, "path": destination, "previous_path": path})
            else:
                changed.append({"status": code, "path": path})
    return {
        "root": str(root),
        "branch": _git(root, "branch", "--show-current") or None,
        "head": _git(root, "rev-parse", "HEAD") or None,
        "changed_files": changed,
        "is_git_repository": bool(_git(root, "rev-parse", "--is-inside-work-tree")),
    }


def _git(cwd: Path, *args: str) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip("\n")

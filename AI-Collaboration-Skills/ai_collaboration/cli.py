"""Command-line interface for AI Collaboration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from . import __version__
from .service import CollaborationService


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-collaboration", description="Cross-agent task continuity"
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--home", type=Path, help="Override AI Collaboration data directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    task = subparsers.add_parser("task", help="Manage continuity tasks")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_start = task_sub.add_parser("start")
    task_start.add_argument("title")
    task_start.add_argument("--description", default="")
    task_start.add_argument("--cwd")
    task_list = task_sub.add_parser("list")
    task_list.add_argument("--cwd")
    task_list.add_argument("--all", action="store_true")
    task_use = task_sub.add_parser("use")
    task_use.add_argument("task_id")
    task_complete = task_sub.add_parser("complete")
    task_complete.add_argument("task_id")

    for name in ("status", "context", "changed-files"):
        command = subparsers.add_parser(name)
        command.add_argument("--cwd")

    sessions = subparsers.add_parser("sessions")
    sessions.add_argument("--task-id")
    sessions.add_argument("--cwd")
    sessions.add_argument("--limit", type=int, default=50)

    events = subparsers.add_parser("events")
    events.add_argument("--task-id")
    events.add_argument("--session-id")
    events.add_argument("--cwd")
    events.add_argument("--limit", type=int, default=100)
    events.add_argument("--payload", action="store_true")

    search = subparsers.add_parser("search")
    search.add_argument("query")
    search.add_argument("--task-id")
    search.add_argument("--cwd")
    search.add_argument("--limit", type=int, default=50)

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("summary")
    checkpoint.add_argument("--next-action", default="")
    checkpoint.add_argument("--provider", default="manual")
    checkpoint.add_argument("--task-id")
    checkpoint.add_argument("--session-id")
    checkpoint.add_argument("--cwd")

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--provider", required=True)
    ingest.add_argument("--event", required=True)
    ingest.add_argument("--file", type=Path)

    subparsers.add_parser("doctor")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = build_parser().parse_args(argv)
    service = CollaborationService.from_home(arguments.home)
    result: Any
    try:
        if arguments.command == "task":
            if arguments.task_command == "start":
                result = service.start_task(arguments.title, arguments.cwd, arguments.description)
            elif arguments.task_command == "list":
                repo_root = None if arguments.all else str(service.repo(arguments.cwd))
                result = service.store.list_tasks(repo_root=repo_root)
            elif arguments.task_command == "use":
                result = service.store.activate_task(arguments.task_id)
            else:
                result = service.store.complete_task(arguments.task_id)
        elif arguments.command == "status":
            result = service.status(arguments.cwd)
        elif arguments.command == "context":
            result = service.context(arguments.cwd)
        elif arguments.command == "changed-files":
            result = service.changed_files(arguments.cwd)
        elif arguments.command == "sessions":
            task_id = arguments.task_id
            if not task_id:
                task = service.current_task(arguments.cwd)
                if not task:
                    raise ValueError("no active task")
                task_id = task["id"]
            result = service.store.list_sessions(task_id, arguments.limit)
        elif arguments.command == "events":
            task_id = arguments.task_id
            if not task_id:
                task = service.current_task(arguments.cwd)
                if not task:
                    raise ValueError("no active task")
                task_id = task["id"]
            result = service.store.list_events(
                task_id=task_id,
                session_id=arguments.session_id,
                limit=arguments.limit,
                include_payload=arguments.payload,
            )
        elif arguments.command == "search":
            result = service.search(
                arguments.query, arguments.cwd, arguments.task_id, arguments.limit
            )
        elif arguments.command == "checkpoint":
            result = service.checkpoint(
                arguments.summary,
                arguments.next_action,
                arguments.provider,
                arguments.cwd,
                arguments.task_id,
                arguments.session_id,
            )
        elif arguments.command == "ingest":
            raw = arguments.file.read_text(encoding="utf-8") if arguments.file else sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
            result = service.ingest(arguments.provider, arguments.event, payload)
        else:
            result = {
                "ok": True,
                "storage": service.store.stats(),
                "repository": service.changed_files(),
                "python": sys.version.split()[0],
            }
        _print(result)
        return 0
    except (KeyError, ValueError, json.JSONDecodeError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

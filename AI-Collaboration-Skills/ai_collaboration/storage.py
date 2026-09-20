"""SQLite event store and content-addressed object storage."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Mapping, Optional

from .config import Settings
from .security import bounded_json

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ObjectStore:
    """Immutable SHA-256 addressed gzip objects."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def put(self, content: bytes) -> str:
        digest = hashlib.sha256(content).hexdigest()
        destination = self.settings.objects / digest[:2] / (digest[2:] + ".json.gz")
        if destination.exists():
            return digest
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix="object-", dir=str(destination.parent))
        try:
            with os.fdopen(descriptor, "wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                    compressed.write(content)
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, destination)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return digest

    def get(self, digest: str) -> bytes:
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("invalid object digest")
        path = self.settings.objects / digest[:2] / (digest[2:] + ".json.gz")
        with gzip.open(path, "rb") as compressed:
            return compressed.read()


class EventStore:
    """Transactional local state for tasks, sessions, events, and checkpoints."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings.load()
        self.settings.ensure()
        self.objects = ObjectStore(self.settings)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.settings.database), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    repo_root TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active', 'completed', 'archived')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_repo_status ON tasks(repo_root, status, updated_at DESC);
                CREATE TABLE IF NOT EXISTS repo_state (
                    repo_root TEXT PRIMARY KEY,
                    active_task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    cwd TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_task ON sessions(task_id, started_at DESC);
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    tool TEXT,
                    command TEXT,
                    exit_code INTEGER,
                    cwd TEXT NOT NULL,
                    git_head TEXT,
                    git_branch TEXT,
                    files_read_json TEXT NOT NULL DEFAULT '[]',
                    files_written_json TEXT NOT NULL DEFAULT '[]',
                    summary TEXT NOT NULL DEFAULT '',
                    payload_inline TEXT,
                    payload_ref TEXT,
                    parent_event_id TEXT REFERENCES events(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_task_time ON events(task_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_events_session_time ON events(session_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type, timestamp DESC);
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
                    provider TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    next_action TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(task_id, created_at DESC);
                """)
            try:
                connection.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS event_search USING fts5(event_id UNINDEXED, summary, command)"
                )
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('fts5', 'enabled')"
                )
            except sqlite3.OperationalError:
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('fts5', 'disabled')"
                )
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        try:
            self.settings.database.chmod(0o600)
        except OSError:
            pass

    def create_task(self, title: str, repo_root: str, description: str = "") -> Dict[str, Any]:
        task_id = uuid.uuid4().hex[:12]
        timestamp = utc_now()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO tasks(id, title, description, repo_root, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'active', ?, ?)",
                (task_id, title, description, repo_root, timestamp, timestamp),
            )
            connection.execute(
                "INSERT INTO repo_state(repo_root, active_task_id, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(repo_root) DO UPDATE SET active_task_id=excluded.active_task_id, updated_at=excluded.updated_at",
                (repo_root, task_id, timestamp),
            )
        return self.get_task(task_id) or {}

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def current_task(self, repo_root: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT tasks.* FROM repo_state JOIN tasks ON tasks.id = repo_state.active_task_id "
                "WHERE repo_state.repo_root = ? AND tasks.status = 'active'",
                (repo_root,),
            ).fetchone()
        return dict(row) if row else None

    def list_tasks(self, repo_root: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tasks"
        parameters: List[Any] = []
        if repo_root:
            query += " WHERE repo_root = ?"
            parameters.append(repo_root)
        query += " ORDER BY updated_at DESC LIMIT ?"
        parameters.append(limit)
        with self.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def activate_task(self, task_id: str) -> Dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            raise KeyError("task not found: %s" % task_id)
        timestamp = utc_now()
        with self.connection() as connection:
            connection.execute(
                "UPDATE tasks SET status='active', updated_at=? WHERE id=?", (timestamp, task_id)
            )
            connection.execute(
                "INSERT INTO repo_state(repo_root, active_task_id, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(repo_root) DO UPDATE SET active_task_id=excluded.active_task_id, updated_at=excluded.updated_at",
                (task["repo_root"], task_id, timestamp),
            )
        return self.get_task(task_id) or {}

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            raise KeyError("task not found: %s" % task_id)
        timestamp = utc_now()
        with self.connection() as connection:
            connection.execute(
                "UPDATE tasks SET status='completed', updated_at=? WHERE id=?", (timestamp, task_id)
            )
            connection.execute(
                "UPDATE repo_state SET active_task_id=NULL, updated_at=? WHERE active_task_id=?",
                (timestamp, task_id),
            )
        return self.get_task(task_id) or {}

    def ensure_session(
        self,
        session_id: str,
        task_id: str,
        provider: str,
        cwd: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        timestamp = utc_now()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO sessions(id, task_id, provider, cwd, started_at, metadata_json) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET task_id=excluded.task_id, provider=excluded.provider, "
                "cwd=excluded.cwd, metadata_json=excluded.metadata_json",
                (session_id, task_id, provider, cwd, timestamp, metadata_json),
            )

    def end_session(self, session_id: str) -> None:
        with self.connection() as connection:
            connection.execute("UPDATE sessions SET ended_at=? WHERE id=?", (utc_now(), session_id))

    def add_event(self, event: Mapping[str, Any], payload: Any) -> Dict[str, Any]:
        event_id = str(event.get("id") or uuid.uuid4().hex)
        encoded = bounded_json(payload, self.settings.max_payload_bytes)
        payload_inline: Optional[str] = None
        payload_ref: Optional[str] = None
        if len(encoded) <= self.settings.inline_payload_bytes:
            payload_inline = encoded.decode("utf-8", errors="replace")
        else:
            payload_ref = self.objects.put(encoded)
        summary = str(event.get("summary") or "")[:4000]
        command = event.get("command")
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO events(
                    id, task_id, session_id, provider, timestamp, event_type, tool, command, exit_code,
                    cwd, git_head, git_branch, files_read_json, files_written_json, summary,
                    payload_inline, payload_ref, parent_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event["task_id"],
                    event["session_id"],
                    event["provider"],
                    event.get("timestamp") or utc_now(),
                    event["event_type"],
                    event.get("tool"),
                    command,
                    event.get("exit_code"),
                    event["cwd"],
                    event.get("git_head"),
                    event.get("git_branch"),
                    json.dumps(event.get("files_read", []), ensure_ascii=False),
                    json.dumps(event.get("files_written", []), ensure_ascii=False),
                    summary,
                    payload_inline,
                    payload_ref,
                    event.get("parent_event_id"),
                ),
            )
            fts = connection.execute("SELECT value FROM metadata WHERE key='fts5'").fetchone()
            if fts and fts[0] == "enabled":
                connection.execute(
                    "INSERT INTO event_search(event_id, summary, command) VALUES (?, ?, ?)",
                    (event_id, summary, command or ""),
                )
            connection.execute(
                "UPDATE tasks SET updated_at=? WHERE id=?", (utc_now(), event["task_id"])
            )
        return self.get_event(event_id, include_payload=False) or {}

    def get_event(self, event_id: str, include_payload: bool = True) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not row:
            return None
        return self._event_dict(row, include_payload)

    def list_events(
        self,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        include_payload: bool = False,
    ) -> List[Dict[str, Any]]:
        clauses = []
        parameters: List[Any] = []
        if task_id:
            clauses.append("task_id = ?")
            parameters.append(task_id)
        if session_id:
            clauses.append("session_id = ?")
            parameters.append(session_id)
        query = "SELECT * FROM events"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC LIMIT ?"
        parameters.append(max(1, min(limit, 1000)))
        with self.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._event_dict(row, include_payload) for row in rows]

    def list_sessions(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT sessions.*, COUNT(events.id) AS event_count FROM sessions "
                "LEFT JOIN events ON events.session_id=sessions.id WHERE sessions.task_id=? "
                "GROUP BY sessions.id ORDER BY sessions.started_at DESC LIMIT ?",
                (task_id, max(1, min(limit, 500))),
            ).fetchall()
        return [dict(row) for row in rows]

    def search(
        self, query: str, task_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with self.connection() as connection:
            fts = connection.execute("SELECT value FROM metadata WHERE key='fts5'").fetchone()
            if fts and fts[0] == "enabled":
                sql = (
                    "SELECT events.* FROM event_search JOIN events ON events.id=event_search.event_id "
                    "WHERE event_search MATCH ?"
                )
                parameters: List[Any] = [query]
                if task_id:
                    sql += " AND events.task_id=?"
                    parameters.append(task_id)
                sql += " ORDER BY bm25(event_search), events.timestamp DESC LIMIT ?"
                parameters.append(limit)
                try:
                    rows = connection.execute(sql, parameters).fetchall()
                except sqlite3.OperationalError:
                    rows = []
            else:
                rows = []
            if not rows:
                pattern = "%%%s%%" % query.replace("%", "\\%").replace("_", "\\_")
                sql = "SELECT * FROM events WHERE (summary LIKE ? ESCAPE '\\' OR command LIKE ? ESCAPE '\\')"
                parameters = [pattern, pattern]
                if task_id:
                    sql += " AND task_id=?"
                    parameters.append(task_id)
                sql += " ORDER BY timestamp DESC LIMIT ?"
                parameters.append(limit)
                rows = connection.execute(sql, parameters).fetchall()
        return [self._event_dict(row, include_payload=False) for row in rows]

    def add_checkpoint(
        self,
        task_id: str,
        provider: str,
        summary: str,
        next_action: str = "",
        session_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        checkpoint_id = uuid.uuid4().hex
        timestamp = utc_now()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO checkpoints(id, task_id, session_id, provider, created_at, summary, next_action, metadata_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    checkpoint_id,
                    task_id,
                    session_id,
                    provider,
                    timestamp,
                    summary,
                    next_action,
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                ),
            )
            row = connection.execute(
                "SELECT * FROM checkpoints WHERE id=?", (checkpoint_id,)
            ).fetchone()
        return dict(row) if row else {}

    def latest_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM checkpoints WHERE task_id=? ORDER BY created_at DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        return dict(row) if row else None

    def stats(self) -> Dict[str, Any]:
        with self.connection() as connection:
            counts = {
                "tasks": connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
                "sessions": connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "events": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                "checkpoints": connection.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0],
            }
            schema = connection.execute(
                "SELECT value FROM metadata WHERE key='schema_version'"
            ).fetchone()
            fts = connection.execute("SELECT value FROM metadata WHERE key='fts5'").fetchone()
        return {
            **counts,
            "schema_version": int(schema[0]) if schema else 0,
            "fts5": fts[0] if fts else "unknown",
            "database": str(self.settings.database),
            "objects": str(self.settings.objects),
        }

    def _event_dict(self, row: sqlite3.Row, include_payload: bool) -> Dict[str, Any]:
        event = dict(row)
        event["files_read"] = json.loads(event.pop("files_read_json"))
        event["files_written"] = json.loads(event.pop("files_written_json"))
        payload_inline = event.pop("payload_inline")
        payload_ref = event.get("payload_ref")
        if include_payload:
            if payload_inline:
                event["payload"] = json.loads(payload_inline)
            elif payload_ref:
                event["payload"] = json.loads(self.objects.get(payload_ref).decode("utf-8"))
            else:
                event["payload"] = None
        return event

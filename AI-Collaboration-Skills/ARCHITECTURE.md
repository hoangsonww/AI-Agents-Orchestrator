# AI Collaboration Architecture

## Boundary

`AI-Collaboration-Skills/` is an independent product package. It uses only the Python standard library and Git. It does not import from the parent repository's orchestrator, agentic-team runtime, MCP server, or context graph.

## Layers

1. **Portable package** — Agent Plugins 1.0 manifest, five Agent Skills, and a stdio MCP server.
2. **Host adapters** — native manifests and lifecycle hook configurations for Claude, Codex, Cursor, Gemini, and Copilot.
3. **Normalization service** — maps vendor payload fields into a provider-neutral event.
4. **Storage** — transactional SQLite rows plus compressed content-addressed payload objects.
5. **Retrieval** — deterministic status, search, test history, and resume context exposed through CLI and MCP.

## Host mapping

| Host | Package manifest | Hook configuration | MCP configuration |
|---|---|---|---|
| Portable | `plugin.json` | client extension | `mcp.json` |
| Claude Code | `.claude-plugin/plugin.json` | `adapters/claude/hooks.json` | `.mcp.json` |
| Codex | `.codex-plugin/plugin.json` compatibility layer | `adapters/codex/hooks.json` via `extensions.com.openai` | portable `mcp.json` |
| Cursor | `.cursor-plugin/plugin.json` | `adapters/cursor/hooks.json` | `adapters/cursor/mcp.json` |
| Gemini CLI | `gemini-extension.json` | `hooks/hooks.json` | inline native config |
| Copilot CLI | portable `plugin.json` | `com.github.copilot/hooks/hooks.json` | portable `mcp.json` |

Gemini and Claude both conventionally inspect `hooks/hooks.json` but use different event schemas. Gemini owns the conventional path; Claude's manifest explicitly selects its adapter file. Cursor and Codex likewise select host-specific files. Copilot uses the Agent Plugins client-extension directory defined by its documentation.

## Data model

```text
Task 1 ──* Session 1 ──* Event
  │                         │
  └────────* Checkpoint     └── payload_inline XOR payload_ref
```

### Task

A named unit of continuity scoped to a canonical repository root. `repo_state` holds at most one active task per repository while completed tasks remain queryable.

### Session

A provider-scoped host session attached to one task. Supplied host IDs are prefixed with the provider. When a host does not provide a session ID, a stable process/repository-derived fallback is used.

### Event

The normalized row stores:

```text
id, task_id, session_id, provider, timestamp, event_type
tool, command, exit_code
cwd, git_head, git_branch
files_read, files_written
summary, payload_inline, payload_ref, parent_event_id
```

Raw payloads are redacted before serialization. Small payloads remain inline; larger payloads are gzip-compressed under a SHA-256 address. This keeps history queries small while deduplicating repeated large results.

### Checkpoint

A deliberate human- or agent-authored milestone containing a summary and concrete next action. Checkpoints supplement passive events and take priority when selecting a suggested next action.

## SQLite behavior

- WAL mode permits concurrent readers and short concurrent writes.
- foreign keys enforce task/session/event ownership.
- indexed task/session timestamps support recent-history queries.
- FTS5 provides ranked summary and command search when available.
- a `LIKE` fallback preserves search on SQLite builds without FTS5 or for invalid FTS query syntax.
- schema version metadata provides a migration anchor for later releases.

## Context algorithm

`get_context` does not call an LLM. It combines:

1. the active repository task;
2. live Git branch, head, and working-tree changes;
3. recent sessions and normalized events;
4. recent files referenced by those events;
5. captured test commands and exit codes;
6. the latest checkpoint;
7. a rule-based next action.

The incoming agent is instructed to verify the current diff before acting because repository state is authoritative and can change outside captured sessions.

## Failure model

- Hook capture is fail-open: errors go to stderr, stdout remains valid JSON, and exit status is zero.
- MCP requests return JSON-RPC errors without contaminating stdout with logs.
- Git inspection uses argument arrays, never `shell=True`, and has a three-second timeout.
- SQLite transactions roll back on errors and use a five-second busy timeout.
- Object files are written to a private temporary file and atomically renamed.

## Extending providers

Add a native manifest or hook config that invokes:

```bash
python3 <plugin-root>/hooks/ingest.py --provider <name> --event <event>
```

Do not add provider logic to storage. Extend normalization only when a provider uses field names the existing aliases cannot interpret. Keep pre-tool hooks disabled on hosts where hook failure can block tools unless the new adapter has a proven fail-open contract.

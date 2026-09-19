# AI Collaboration

AI Collaboration is a self-contained cross-agent task-continuity plugin for Claude Code, Codex, Cursor, Gemini CLI, and GitHub Copilot CLI. It captures lifecycle events locally, stores normalized history in SQLite, and gives the next agent focused context through portable Agent Skills, MCP tools, and a CLI.

It does not depend on either runtime in the parent repository and never imports from `orchestrator/` or `agentic_team/`.

## What it provides

- Agent Plugins 1.0 portable package (`plugin.json`, `mcp.json`, and `skills/`)
- native manifests and lifecycle hooks for five coding-agent hosts
- private SQLite task, session, event, and checkpoint storage
- SHA-256 content-addressed gzip objects for large payloads
- automatic secret-field and bearer-token redaction
- read-only Git branch, head, and working-tree capture
- deterministic context assembly without an LLM call
- dependency-free Python 3.8+ CLI and MCP stdio server

## Requirements

- Python 3.8 or newer available as `python3`
- Git for repository-state capture
- one supported agent host

No Python packages need to be installed.

## Install from this repository

Clone the parent repository, then use `AI-Collaboration-Skills/` as the plugin root.

### Claude Code

```bash
claude plugin marketplace add ./AI-Collaboration-Skills
claude plugin install ai-collaboration@ai-collaboration
```

For a one-session development load:

```bash
claude --plugin-dir ./AI-Collaboration-Skills
```

### Codex

```bash
codex plugin marketplace add ./AI-Collaboration-Skills
codex plugin add ai-collaboration@ai-collaboration
```

Codex asks users to review and trust bundled hooks before executing them.

### Cursor

Cursor discovers development plugins below `~/.cursor/plugins/local`:

```bash
mkdir -p ~/.cursor/plugins/local
cp -R ./AI-Collaboration-Skills ~/.cursor/plugins/local/ai-collaboration
```

Restart Cursor or run `Developer: Reload Window`, then confirm the plugin in Customize. Organizations can disable local plugin imports.

### Gemini CLI

```bash
gemini extensions install ./AI-Collaboration-Skills
```

For development without copying:

```bash
gemini extensions link ./AI-Collaboration-Skills
```

### GitHub Copilot CLI

```bash
copilot plugin install ./AI-Collaboration-Skills
copilot plugin list
```

## First use

Start an explicit continuity task from the repository being edited:

```bash
/path/to/AI-Collaboration-Skills/bin/ai-collaboration task start "Fix session ownership isolation"
```

Hooks attach later sessions and events to the active task for that Git repository. A session without an explicit task creates an active task named `Continue work in <repository>` so passive capture is never discarded.

Useful CLI commands:

```bash
bin/ai-collaboration status
bin/ai-collaboration context
bin/ai-collaboration sessions
bin/ai-collaboration search "ownership validation"
bin/ai-collaboration checkpoint "Validation added" --next-action "Run the focused tests"
bin/ai-collaboration task list
bin/ai-collaboration doctor
```

Every command emits JSON for scripting.

## Skills

| Skill | Purpose |
|---|---|
| `resume-task` | Verify and continue work from another agent |
| `inspect-history` | Search prior events without changing files |
| `collaboration-status` | Summarize task, sessions, Git state, and checkpoint |
| `create-checkpoint` | Save a durable milestone and next action |
| `handoff-task` | Prepare a verified intentional handoff |

Hosts namespace or display skills according to their own conventions. For example, Claude Code exposes plugin skills under the `ai-collaboration` namespace.

## MCP tools

| Tool | Behavior |
|---|---|
| `ai_collaboration.current_task` | Get the repository's active task |
| `ai_collaboration.status` | Get task, session, checkpoint, recent-event, and Git state |
| `ai_collaboration.sessions` | List sessions for a task |
| `ai_collaboration.search_history` | Search event summaries and commands |
| `ai_collaboration.session_events` | Expand one session's event history |
| `ai_collaboration.changed_files` | Inspect current Git changes |
| `ai_collaboration.test_history` | List captured test commands and exit codes |
| `ai_collaboration.get_context` | Build deterministic resume context |
| `ai_collaboration.record_checkpoint` | Store an intentional handoff checkpoint |
| `ai_collaboration.start_task` | Create and activate a task |

## Captured data

Hooks record the fields each host provides, normalized into:

- task, session, provider, timestamp, and event type
- tool name, command, and exit code
- current working directory, Git head, and branch
- files read or written when the payload identifies them
- a redacted raw payload, inline or content-addressed

The default store is shared by every host:

```text
~/.ai-collaboration/
├── ai-collaboration.db
└── objects/
    └── <sha256-prefix>/<sha256-rest>.json.gz
```

Set `AI_COLLABORATION_HOME` in the environment of every host to use another shared location.

See [PRIVACY.md](PRIVACY.md) for the threat model, redaction boundaries, and retention guidance.

## Hook behavior

The passive layer never asks a model to decide whether to capture an event. Every hook:

- reads JSON from stdin;
- writes one normalized local event;
- prints `{}` to stdout;
- exits zero even if capture fails.

This fail-open design ensures telemetry cannot block an agent tool call. Cursor and Copilot omit pre-tool capture because those hosts can treat a malformed or failed pre-tool hook as a denial. Post-tool and failure events still capture outcomes.

## Architecture

```text
Claude / Codex / Cursor / Gemini / Copilot
                  │ lifecycle JSON
                  ▼
          host-native hook config
                  │
                  ▼
          shared ingest dispatcher
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
 SQLite event store    compressed objects
       │
       ├── CLI
       ├── MCP tools
       └── Agent Skills
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for schemas, normalization, and host mappings.

## Validation

Run the standalone suite:

```bash
python -m pytest AI-Collaboration-Skills/tests -q --override-ini='addopts=' --timeout=30
```

Validate host packaging when the corresponding CLI is installed:

```bash
claude plugin validate ./AI-Collaboration-Skills --strict
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py ./AI-Collaboration-Skills
```

The tests cover storage, redaction, concurrent ingestion, normalization, Git capture, task lifecycle, checkpoints, CLI entry points, manifest invariants, hooks, and MCP JSON-RPC behavior.

## Standards and host documentation

- [Agent Plugins 1.0](https://agent-plugins.org/specification)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Cursor plugins](https://docs.cursor.com/plugins)
- [Gemini CLI extensions](https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/reference.md)
- [GitHub Copilot plugins](https://docs.github.com/en/copilot/concepts/agents/about-plugins)

---
name: inspect-history
description: Investigate prior AI coding activity, commands, tool outcomes, files, sessions, and tests for an active continuity task without changing project files.
---

# Inspect History

Treat history inspection as read-only unless the user separately requests implementation.

1. Get the active task with `ai_collaboration.current_task`.
2. Use `ai_collaboration.search_history` with a narrow query derived from the user's question.
3. Expand a specific session with `ai_collaboration.session_events` only when needed.
4. Cross-check historical claims against current Git state with `ai_collaboration.changed_files`.
5. Distinguish captured facts from inferences and note when a provider did not emit a field.

Do not dump full payloads by default. Request `include_payload` only when summaries omit necessary evidence; payloads are redacted but can still contain sensitive project content.

If MCP is unavailable, use `bin/ai-collaboration search <query>` and `bin/ai-collaboration events`.

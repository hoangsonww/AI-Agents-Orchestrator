---
name: resume-task
description: Resume an in-progress coding task previously worked on by this or another AI agent using captured local context, Git state, test history, and checkpoints.
---

# Resume Task

Use `ai_collaboration.get_context` for the current repository. If no active task exists, explain that clearly and offer to start one; do not infer a task from unrelated history.

Before editing:

1. Compare the returned Git branch, head, and changed files with the latest captured events.
2. Read the most recent checkpoint and failed test, if present.
3. Inspect the actual diff and relevant files; captured history is evidence, not a substitute for current repository state.
4. State the task, previous provider, important files, last test result, and intended next action in a compact update.

Search with `ai_collaboration.search_history` only when the initial context does not answer a specific question. Continue within the user's existing authorization and repository instructions.

If MCP is unavailable, run `bin/ai-collaboration context --cwd <repository>` from the plugin directory.

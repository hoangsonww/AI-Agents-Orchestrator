---
name: handoff-task
description: Prepare an intentional coding-task handoff to another AI agent with verified repository state, focused history, test results, and a durable checkpoint.
---

# Handoff Task

Use this skill only when the user requests a handoff or asks another agent to continue.

1. Call `ai_collaboration.get_context` and inspect the actual Git diff.
2. Resolve discrepancies between current files and captured history in favor of current repository state.
3. Record a checkpoint with `ai_collaboration.record_checkpoint` containing completed work, remaining work, decisions, known failures, and one concrete next action.
4. Return a compact handoff containing the task ID, repository and branch, changed files, tests, checkpoint, and suggested first action.

Do not commit, push, open a pull request, or mark the task complete unless the user explicitly requested those actions. Do not include raw secrets or unnecessary transcript content.

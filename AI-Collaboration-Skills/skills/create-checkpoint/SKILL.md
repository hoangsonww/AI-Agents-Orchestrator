---
name: create-checkpoint
description: Record a concise, durable checkpoint for an active coding task when the user asks to save progress, mark a milestone, or prepare continuity.
---

# Create Checkpoint

Confirm there is an active task with `ai_collaboration.current_task`. Then inspect current Git state and recent test history before writing a checkpoint.

Call `ai_collaboration.record_checkpoint` with:

- `summary`: what is complete, what remains, material decisions, and known risks;
- `next_action`: one concrete action the next agent can perform;
- `provider`: the current agent name when known.

Do not claim tests passed unless a captured or freshly observed result supports it. Do not include secrets or paste large logs. A checkpoint records context; it does not commit, push, or change task status.

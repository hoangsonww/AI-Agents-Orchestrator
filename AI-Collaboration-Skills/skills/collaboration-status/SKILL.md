---
name: collaboration-status
description: Report the active AI Collaboration task, participating agent sessions, current Git state, recent activity, and latest checkpoint.
---

# Collaboration Status

Call `ai_collaboration.status` for the current repository and report:

- active task ID, title, and status;
- current branch, head, and changed-file count;
- providers and session event counts;
- latest checkpoint and recent failures;
- the most useful next action supported by the data.

Keep this operation read-only. If there is no active task, say so and offer to call `ai_collaboration.start_task` with the user's title.

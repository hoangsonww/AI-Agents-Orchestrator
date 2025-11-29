# Using Progress Logs in the UI

## Quick Start

The AI Orchestrator UI now shows real-time progress logs so you can see what's happening during task execution.

## Where to Find Progress Logs

### 1. Live Progress Widget (Sidebar)
**When**: Only visible during task execution  
**Location**: Bottom of the left sidebar  
**What it shows**: Last 5 log messages in real-time  
**Purpose**: Quick glance at current progress without switching tabs

#### What you'll see:
- 🔵 Blue indicator: "Running" with animated pulse
- Last 5 log messages updating in real-time
- Link to view full logs in dedicated tab

### 2. Full Logs Tab (Main Content Area)
**When**: Always available  
**Location**: Click the "Logs" tab in the main content area  
**What it shows**: Complete log history from start to finish  
**Purpose**: Detailed view of entire execution flow

#### Features:
- **Terminal-style display**: Dark background with colored text
- **Timestamps**: Each log entry shows the exact time
- **Color coding**: Different colors for different log levels
- **Scrollable**: Auto-scrolls to show latest logs
- **Clear button**: Start fresh with a clear log view

## Understanding Log Colors

| Color | Level | Meaning | Example |
|-------|-------|---------|---------|
| 🔵 Blue | INFO | Normal progress | "Executing task: Create a calculator" |
| 🟢 Green | SUCCESS | Successful operation | "Task completed successfully" |
| 🟡 Yellow | WARNING | Non-critical issue | "Agent gemini not available" |
| 🔴 Red | ERROR | Error occurred | "Failed to execute task" |

## Common Log Messages

### Starting Execution
```
[INFO] Starting task execution with workflow: default
[INFO] Executing task: Create a Python calculator
[INFO] Workflow: default
```

### During Execution
```
[INFO] ============================================================
[INFO] Iteration 1/3
[INFO] ============================================================
[INFO] Step 1: codex - implement
[INFO] Step 2: gemini - review
[INFO] Step 3: claude - refine
```

### Completion
```
[SUCCESS] Task execution completed
[INFO] Stopping iterations: task appears complete
```

### Errors
```
[ERROR] Agent codex not available
[ERROR] Failed to execute task: Connection timeout
```

## Tips

1. **Keep an eye on the sidebar**: The live progress widget gives you instant feedback without changing tabs

2. **Switch to Logs tab for details**: If something seems wrong, check the full logs for detailed information

3. **Clear logs between tasks**: Use the "Clear Logs" button to start fresh for a new task

4. **Watch for errors**: Red messages indicate problems that need attention

5. **Check timestamps**: If execution seems slow, timestamps help identify bottlenecks

## Example Workflow

1. **Enter a task** in the sidebar
2. **Click "Execute Task"**
3. **Watch the Live Progress widget** appear in the sidebar
4. **See real-time updates** as each step executes
5. **If needed, click "Logs" tab** for full details
6. **Review the complete log** after execution finishes

## Troubleshooting

### No logs appearing?
- Check that you're connected to the backend (look for connection status)
- Ensure WebSocket connection is active
- Try refreshing the browser

### Logs not updating?
- Check browser console for errors
- Verify backend is running on the correct port
- Check that the task is actually executing

### Old logs cluttering the view?
- Click "Clear Logs" button in the Logs tab
- Or click "Clear" in the header to reset everything

## Benefits

✅ **Know what's happening** - No more wondering if it's working  
✅ **Catch errors early** - See problems as they occur  
✅ **Debug faster** - Detailed logs help identify issues  
✅ **Build confidence** - Visual feedback that progress is being made  
✅ **Learn the process** - Understand how the orchestrator works

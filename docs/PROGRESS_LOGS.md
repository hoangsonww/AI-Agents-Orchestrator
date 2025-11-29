# Real-Time Progress Logs

The UI now displays real-time progress logs to users during task execution, providing visibility into what the orchestrator is doing at each step.

## Features

### 1. Live Progress Sidebar Widget
- **Location**: Sidebar (bottom section)
- **Visibility**: Only shown when a task is running
- **Content**: Shows the last 5 log messages in real-time
- **Styling**: Dark terminal-style display with color-coded log levels

### 2. Full Logs Tab
- **Location**: Main content area (new "Logs" tab)
- **Content**: Complete log history from task start to finish
- **Features**:
  - Auto-scroll to latest logs
  - Color-coded by log level (info, success, warning, error)
  - Timestamps for each log entry
  - Clear logs button

### 3. Log Levels
The system uses different colors for different log levels:
- **INFO** (Blue): General progress information
- **SUCCESS** (Green): Successful operations
- **WARNING** (Yellow): Non-critical issues
- **ERROR** (Red): Errors and failures

## Backend Implementation

### WebSocketLogHandler
A custom logging handler (`WebSocketLogHandler`) captures logs from the orchestrator and emits them to connected clients via WebSocket.

```python
class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that emits logs via WebSocket."""
    
    def __init__(self, socketio_instance):
        super().__init__()
        self.socketio = socketio_instance
        
    def emit(self, record):
        """Emit log record via WebSocket."""
        # Filter to only emit orchestrator-related logs
        if not any(record.name.startswith(prefix) for prefix in 
                  ['orchestrator', 'workflow', 'adapter', 'task_manager']):
            return
            
        log_entry = self.format(record)
        level = record.levelname.lower()
        
        self.socketio.emit('progress_log', {
            'message': log_entry,
            'level': level,
            'timestamp': datetime.now().isoformat()
        })
```

The handler is attached to the root logger during task execution, capturing all logs from:
- `orchestrator` - Main orchestration logic
- `workflow` - Workflow execution steps
- `adapter.*` - All AI agent adapters (codex, gemini, claude, etc.)
- `task_manager` - Task management operations

### WebSocket Events
- **`progress_log`**: Emitted for each log message with message, level, and timestamp
- **`task_started`**: Emitted when a task begins execution
- **`task_completed`**: Emitted when a task finishes successfully
- **`task_error`**: Emitted when a task encounters an error

## Frontend Implementation

### Store (orchestrator.js)
- Maintains a `logs` array to store all log messages
- Listens for `progress_log` WebSocket events
- Provides computed property `hasLogs` to check if logs exist

### UI Components
1. **Sidebar.vue**: Shows live progress widget during execution
2. **MainContent.vue**: Includes full logs tab with all historical logs

## Usage

Users can now:
1. **Monitor Progress**: Watch live updates in the sidebar as tasks execute
2. **View Full History**: Switch to the "Logs" tab to see complete execution logs
3. **Understand Errors**: Quickly identify issues through color-coded error messages
4. **Debug Issues**: Review timestamps and detailed log messages

## Benefits

- **Transparency**: Users know what's happening at all times
- **Debugging**: Easier to diagnose issues with detailed logs
- **Confidence**: Visual feedback that the system is working
- **User Experience**: No more wondering if the system is frozen or still processing

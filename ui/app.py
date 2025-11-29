"""
Web UI Backend for AI Orchestrator

Provides a REST API and WebSocket interface for the web-based UI with conversation support.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that emits logs via WebSocket."""

    def __init__(self, socketio_instance):
        super().__init__()
        self.socketio = socketio_instance
        # Set a simple formatter
        formatter = logging.Formatter("%(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit log record via WebSocket."""
        try:
            if not any(
                record.name.startswith(prefix)
                for prefix in ["orchestrator", "workflow", "adapter", "task_manager"]
            ):
                return

            log_entry = self.format(record)
            level = record.levelname.lower()
            timestamp = datetime.now().isoformat()

            try:
                # Attempt to parse structured JSON log
                log_data = json.loads(log_entry)
                payload = {**log_data, "level": level, "timestamp": timestamp}
            except json.JSONDecodeError:
                # Fallback for plain string logs
                payload = {"message": log_entry, "level": level, "timestamp": timestamp}

            self.socketio.emit("progress_log", payload)
        except Exception as e:
            print(f"[WebSocketLogHandler] Error: {e}")
            pass


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import Orchestrator

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "ai-orchestrator-secret-key-change-in-production"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[Any] = None
current_session: Dict[str, Any] = {
    "task": None,
    "workflow": "default",
    "status": "idle",
    "results": None,
    "files": [],
    "conversation_history": [],
    "last_task": None,
    "last_output": None,
    "context": {},
}


def init_orchestrator() -> None:
    """Initialize the orchestrator."""
    global orchestrator
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"
    orchestrator = Orchestrator(str(config_path))


@app.route("/")
def index():
    """Serve the main UI page."""
    return render_template("index.html")


@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Get list of available agents."""
    if not orchestrator:
        init_orchestrator()

    agents_config = orchestrator.config.get("agents", {})
    agents_list = []

    for name, adapter in orchestrator.adapters.items():
        agent_config = agents_config.get(name, {})
        agents_list.append(
            {
                "name": name,
                "enabled": agent_config.get("enabled", False),
                "role": agent_config.get("role", ""),
                "description": agent_config.get("description", ""),
                "available": adapter.is_available(),
            }
        )

    return jsonify({"agents": agents_list})


@app.route("/api/workflows", methods=["GET"])
def get_workflows():
    """Get list of available workflows."""
    if not orchestrator:
        init_orchestrator()

    workflows_config = orchestrator.config.get("workflows", {})
    workflows_list = []

    for name, steps in workflows_config.items():
        workflow_info = {
            "name": name,
            "steps": [
                {
                    "agent": step.get("agent"),
                    "task": step.get("task"),
                    "description": step.get("description", ""),
                }
                for step in steps
            ],
        }
        workflows_list.append(workflow_info)

    return jsonify({"workflows": workflows_list})


@app.route("/api/execute", methods=["POST"])
def execute_task():
    """Execute a task via the API with conversation support."""
    data = request.json
    task = data.get("task")
    workflow = data.get("workflow", "default")
    max_iterations = data.get("max_iterations", 3)
    is_followup = data.get("is_followup", False)

    if not task:
        return jsonify({"error": "Task is required"}), 400

    if not orchestrator:
        init_orchestrator()

    # Handle follow-up context
    actual_task = task
    if is_followup and current_session.get("last_task"):
        # Inject previous context for follow-ups
        previous_task = current_session["last_task"]
        previous_output = current_session.get("last_output", "")
        actual_task = f"Previous task: {previous_task}\nPrevious result: {previous_output}\n\nFollow-up: {task}"

    # Update session
    current_session["task"] = task
    current_session["workflow"] = workflow
    current_session["status"] = "running"
    current_session["files"] = []

    # Add to conversation history
    current_session["conversation_history"].append(
        {
            "role": "user",
            "content": task,
            "is_followup": is_followup,
            "timestamp": datetime.now().isoformat(),
        }
    )

    # Execute via socket for real-time updates
    socketio.start_background_task(
        execute_task_async, actual_task, workflow, max_iterations, is_followup
    )

    return jsonify(
        {
            "message": "Task started",
            "session_id": datetime.now().isoformat(),
            "is_followup": is_followup,
        }
    )


def execute_task_async(task: str, workflow: str, max_iterations: int, is_followup: bool = False):
    """Execute task asynchronously and send updates via WebSocket."""
    global current_session

    try:
        # Send start event (broadcast to all clients)
        socketio.emit(
            "task_started", {"task": task, "workflow": workflow, "is_followup": is_followup}
        )

        # Emit progress log
        socketio.emit(
            "progress_log",
            {"message": f"Starting task execution with workflow: {workflow}", "level": "info"},
        )

        # Setup logging handler to capture all orchestrator-related logs
        log_handler = WebSocketLogHandler(socketio)
        log_handler.setLevel(logging.INFO)

        # Attach to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        # Debug: verify handler is attached
        print(
            f"[DEBUG] WebSocketLogHandler attached. Root logger handlers: {len(root_logger.handlers)}"
        )
        print(f"[DEBUG] Root logger level: {root_logger.level}")

        # Keep track for cleanup
        loggers_to_capture = [root_logger]

        try:
            # Execute task
            results = orchestrator.execute_task(
                task=task, workflow_name=workflow, max_iterations=max_iterations
            )
        finally:
            # Remove handler after execution from all loggers
            for logger_obj in loggers_to_capture:
                logger_obj.removeHandler(log_handler)

        # Emit completion log
        socketio.emit("progress_log", {"message": "Task execution completed", "level": "success"})

        # Collect files from all iterations
        files_created = []
        for iteration in results.get("iterations", []):
            for step in iteration.get("steps", []):
                if step.get("files_modified"):
                    files_created.extend(step["files_modified"])

        current_session["results"] = results
        current_session["files"] = files_created
        current_session["status"] = "completed" if results.get("success") else "failed"

        # Store for future follow-ups
        final_output = results.get("final_output", "")
        current_session["last_task"] = current_session["task"]
        current_session["last_output"] = final_output
        current_session["context"]["files"] = files_created
        current_session["context"]["workspace"] = "./workspace"

        # Add to conversation history
        current_session["conversation_history"].append(
            {
                "role": "assistant",
                "content": final_output,
                "files": files_created,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Send completion event
        socketio.emit(
            "task_completed",
            {
                "task": current_session["task"],
                "success": results.get("success"),
                "output": final_output,
                "files": files_created,
                "iterations": results.get("iterations", []),
                "can_followup": True,
            },
        )

    except Exception as e:
        logger.error(f"Error executing task: {e}", exc_info=True)
        current_session["status"] = "error"
        socketio.emit("progress_log", {"message": f"Task error: {str(e)}", "level": "error"})
        socketio.emit("task_error", {"error": str(e)})


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current session status."""
    return jsonify(current_session)


@app.route("/api/conversation", methods=["GET"])
def get_conversation():
    """Get conversation history."""
    return jsonify(
        {
            "history": current_session.get("conversation_history", []),
            "can_followup": bool(current_session.get("last_task")),
        }
    )


@app.route("/api/conversation/clear", methods=["POST"])
def clear_conversation():
    """Clear conversation history and start fresh."""
    global current_session
    current_session = {
        "task": None,
        "workflow": "default",
        "status": "idle",
        "results": None,
        "files": [],
        "conversation_history": [],
        "last_task": None,
        "last_output": None,
        "context": {},
    }
    return jsonify({"message": "Conversation cleared"})


@app.route("/api/files/<path:filename>", methods=["GET"])
def get_file(filename):
    """Get file content."""
    workspace_dir = Path(__file__).parent.parent / "workspace"
    file_path = workspace_dir / filename

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    try:
        with open(file_path) as f:
            content = f.read()

        return jsonify(
            {"filename": filename, "content": content, "language": detect_language(filename)}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def detect_language(filename: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "cpp",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sh": "shell",
        ".sql": "sql",
    }

    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "plaintext")


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    emit(
        "connected",
        {
            "message": "Connected to AI Orchestrator",
            "can_followup": bool(current_session.get("last_task")),
        },
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")


if __name__ == "__main__":
    init_orchestrator()
    port = int(os.environ.get("UI_BACKEND_PORT") or os.environ.get("PORT", "5001"))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)

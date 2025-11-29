"""
Task management and distribution.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task to be executed."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self, agent: str):
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.assigned_agent = agent

    def complete(self, result: Any):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def fail(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class TaskManager:
    """Manages tasks and their execution."""

    def __init__(self):
        self.logger = logging.getLogger("task_manager")
        self.tasks: Dict[str, Task] = {}
        self.task_counter = 0

    def create_task(self, description: str, metadata: Optional[Dict] = None) -> Task:
        """
        Create a new task.

        Args:
            description: Task description
            metadata: Optional metadata

        Returns:
            Created task
        """
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"

        task = Task(id=task_id, description=description, metadata=metadata or {})

        self.tasks[task_id] = task
        self.logger.info(f"Created task: {task_id}")

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return [task for task in self.tasks.values() if task.status == status]

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return self.get_tasks_by_status(TaskStatus.PENDING)

    def get_active_tasks(self) -> List[Task]:
        """Get all in-progress tasks."""
        return self.get_tasks_by_status(TaskStatus.IN_PROGRESS)

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks."""
        return self.get_tasks_by_status(TaskStatus.COMPLETED)

    def get_statistics(self) -> Dict[str, Any]:
        """Get task execution statistics."""
        all_tasks = list(self.tasks.values())

        if not all_tasks:
            return {
                "total_tasks": 0,
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "failed": 0,
                "average_duration": 0,
            }

        completed_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
        durations = [t.duration() for t in completed_tasks if t.duration() is not None]

        return {
            "total_tasks": len(all_tasks),
            "pending": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "in_progress": len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]),
            "completed": len(completed_tasks),
            "failed": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
            "average_duration": sum(durations) / len(durations) if durations else 0,
        }

    def clear_completed(self):
        """Remove completed tasks."""
        self.tasks = {
            task_id: task
            for task_id, task in self.tasks.items()
            if task.status != TaskStatus.COMPLETED
        }
        self.logger.info("Cleared completed tasks")

    def clear_all(self):
        """Clear all tasks."""
        self.tasks.clear()
        self.task_counter = 0
        self.logger.info("Cleared all tasks")

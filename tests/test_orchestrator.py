"""
Tests for orchestrator core functionality
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from adapters import AgentCapability, AgentResponse, BaseAdapter
from orchestrator import Orchestrator, TaskManager, WorkflowEngine, WorkflowStep


class TestOrchestrator:
    """Test Orchestrator functionality."""

    def test_initialization_with_default_config(self):
        """Test orchestrator initialization with default config."""
        orchestrator = Orchestrator(config_path=None)

        assert orchestrator.config is not None
        assert "agents" in orchestrator.config
        assert "workflows" in orchestrator.config

    def test_initialization_with_custom_config(self, sample_config, tmp_path):
        """Test orchestrator initialization with custom config."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)

        orchestrator = Orchestrator(config_path=str(config_file))

        assert orchestrator.config["agents"]["test_agent"]["enabled"] is True

    def test_get_available_agents(self, sample_config, tmp_path):
        """Test getting list of available agents."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)

        with patch.object(BaseAdapter, "is_available", return_value=True):
            orchestrator = Orchestrator(config_path=str(config_file))
            # Available agents depends on which CLI tools are installed
            agents = orchestrator.get_available_agents()
            assert isinstance(agents, list)

    def test_get_workflows(self, sample_config, tmp_path):
        """Test getting list of workflows."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)

        orchestrator = Orchestrator(config_path=str(config_file))
        workflows = orchestrator.get_workflows()

        assert "test_workflow" in workflows


class TestWorkflowEngine:
    """Test WorkflowEngine functionality."""

    def test_workflow_initialization(self):
        """Test workflow engine initialization."""
        engine = WorkflowEngine()

        assert engine.steps == []
        assert engine.current_step == 0

    def test_set_workflow(self):
        """Test setting workflow steps."""
        engine = WorkflowEngine()

        mock_adapter = Mock(spec=BaseAdapter)
        steps = [
            WorkflowStep(agent_name="test", task_type="implement", adapter=mock_adapter, config={})
        ]

        engine.set_workflow(steps)

        assert len(engine.steps) == 1
        assert engine.current_step == 0

    def test_get_progress(self):
        """Test getting workflow progress."""
        engine = WorkflowEngine()

        mock_adapter = Mock(spec=BaseAdapter)
        steps = [
            WorkflowStep("test1", "implement", mock_adapter, {}),
            WorkflowStep("test2", "review", mock_adapter, {}),
        ]

        engine.set_workflow(steps)
        engine.current_step = 1

        progress = engine.get_progress()

        assert progress["current_step"] == 1
        assert progress["total_steps"] == 2
        assert progress["progress_percent"] == 50.0


class TestWorkflowStep:
    """Test WorkflowStep functionality."""

    def test_build_task_description(self):
        """Test building task descriptions."""
        mock_adapter = Mock(spec=BaseAdapter)

        step = WorkflowStep(
            agent_name="test", task_type="implement", adapter=mock_adapter, config={}
        )

        context = {"task": "Create a function"}

        description = step._build_task_description(context)

        assert "Create a function" in description
        assert "Implement" in description

    def test_execute_step(self):
        """Test executing a workflow step."""
        mock_adapter = Mock(spec=BaseAdapter)
        mock_adapter.execute_task.return_value = AgentResponse(success=True, output="Test output")

        step = WorkflowStep(
            agent_name="test", task_type="implement", adapter=mock_adapter, config={}
        )

        context = {"task": "Test task"}
        response = step.execute(context)

        assert response.success is True
        assert response.output == "Test output"
        mock_adapter.execute_task.assert_called_once()


class TestTaskManager:
    """Test TaskManager functionality."""

    def test_create_task(self):
        """Test creating a task."""
        manager = TaskManager()

        task = manager.create_task("Test task")

        assert task.id == "task_1"
        assert task.description == "Test task"
        assert task.status.value == "pending"

    def test_get_task(self):
        """Test getting a task by ID."""
        manager = TaskManager()

        task = manager.create_task("Test task")
        retrieved = manager.get_task("task_1")

        assert retrieved is task

    def test_get_pending_tasks(self):
        """Test getting pending tasks."""
        manager = TaskManager()

        task1 = manager.create_task("Task 1")
        task2 = manager.create_task("Task 2")
        task1.start("agent1")

        pending = manager.get_pending_tasks()

        assert len(pending) == 1
        assert task2 in pending

    def test_get_statistics(self):
        """Test getting task statistics."""
        manager = TaskManager()

        task1 = manager.create_task("Task 1")
        task2 = manager.create_task("Task 2")

        task1.start("agent1")
        task1.complete("result")

        task2.start("agent2")
        task2.fail("error")

        stats = manager.get_statistics()

        assert stats["total_tasks"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1

    def test_clear_completed(self):
        """Test clearing completed tasks."""
        manager = TaskManager()

        task1 = manager.create_task("Task 1")
        task2 = manager.create_task("Task 2")

        task1.start("agent1")
        task1.complete("result")

        manager.clear_completed()

        assert len(manager.tasks) == 1
        assert task2.id in manager.tasks

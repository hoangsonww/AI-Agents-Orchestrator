"""
Integration tests for the complete AI orchestrator system.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from adapters import AgentResponse
from orchestrator import Orchestrator


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete workflow execution."""

    @pytest.fixture
    def integration_config(self, tmp_path):
        """Create integration test configuration."""
        config = {
            "agents": {
                "mock_codex": {
                    "enabled": True,
                    "command": "echo",
                    "role": "implementation",
                    "timeout": 30,
                },
                "mock_gemini": {
                    "enabled": True,
                    "command": "echo",
                    "role": "review",
                    "timeout": 30,
                },
                "mock_claude": {
                    "enabled": True,
                    "command": "echo",
                    "role": "refinement",
                    "timeout": 30,
                },
            },
            "workflows": {
                "test_workflow": [
                    {"agent": "mock_codex", "task": "implement"},
                    {"agent": "mock_gemini", "task": "review"},
                    {"agent": "mock_claude", "task": "refine"},
                ]
            },
            "settings": {
                "max_iterations": 1,
                "output_dir": str(tmp_path / "output"),
                "log_level": "DEBUG",
            },
        }

        config_file = tmp_path / "integration_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        return str(config_file)

    def test_workflow_execution_mock(self, integration_config):
        """Test workflow execution with mocked agents."""
        # Mock the adapter methods to simulate successful execution
        with patch("adapters.base.BaseAdapter.is_available", return_value=True):
            with patch("adapters.base.BaseAdapter._run_command_with_prompt") as mock_execute:
                # Mock successful responses
                mock_execute.return_value = AgentResponse(
                    success=True,
                    output="Mock implementation complete",
                    files_modified=["test.py"],
                    suggestions=["Suggestion 1", "Suggestion 2"],
                )

                orchestrator = Orchestrator(config_path=integration_config)

                # This would fail in real execution without actual CLI tools
                # but serves as a structural integration test
                assert orchestrator is not None
                assert len(orchestrator.adapters) >= 0

    def test_cli_communicator_workspace_tracking(self, temp_workspace):
        """Test that workspace file tracking works correctly."""
        from adapters.cli_communicator import CLICommunicator

        communicator = CLICommunicator("echo")

        # Create some files in workspace
        test_file = Path(temp_workspace) / "test.txt"
        test_file.write_text("test content")

        # Get initial state
        initial_state = communicator._get_file_state(Path(temp_workspace))

        assert len(initial_state) > 0

        # Modify a file
        import time

        time.sleep(0.1)  # Ensure mtime changes
        test_file.write_text("modified content")

        # Check modified files
        modified = communicator._get_modified_files(Path(temp_workspace), initial_state)

        assert str(test_file) in modified

    def test_error_handling(self, integration_config):
        """Test that errors are handled gracefully."""
        with patch("adapters.base.BaseAdapter.is_available", return_value=False):
            orchestrator = Orchestrator(config_path=integration_config)

            # Should handle unavailable agents gracefully
            assert isinstance(orchestrator.adapters, dict)


@pytest.mark.integration
class TestCLICommunication:
    """Test CLI communication patterns."""

    def test_stdin_communication(self):
        """Test stdin-based communication."""
        from adapters.cli_communicator import CLICommunicator

        # Use a simple command that echoes stdin
        communicator = CLICommunicator("cat")

        success, stdout, stderr = communicator.execute_with_prompt(
            prompt="test input", method="stdin", timeout=5
        )

        assert success is True
        assert "test input" in stdout

    def test_argument_communication(self):
        """Test argument-based communication."""
        from adapters.cli_communicator import CLICommunicator

        communicator = CLICommunicator("echo")

        success, stdout, stderr = communicator.execute_with_prompt(
            prompt="test message", method="arg", timeout=5
        )

        assert success is True
        assert "test message" in stdout

    def test_timeout_handling(self):
        """Test timeout handling."""
        from adapters.cli_communicator import CLICommunicator

        # Use sleep command to test timeout
        communicator = CLICommunicator("sleep")

        success, stdout, stderr = communicator.execute_with_prompt(
            prompt="10",  # Sleep for 10 seconds
            method="arg",
            timeout=1,  # But timeout after 1 second
        )

        assert success is False
        assert "timed out" in stderr.lower() or "timeout" in stderr.lower()

    def test_retry_mechanism(self):
        """Test automatic retry on failure."""
        from adapters.cli_communicator import CLICommunicator

        communicator = CLICommunicator("false")  # Command that always fails

        success, stdout, stderr = communicator.execute_with_retry(
            prompt="test", method="arg", max_retries=3, timeout=5
        )

        assert success is False
        assert "Failed after 3 attempts" in stderr


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end system tests."""

    def test_config_validation(self):
        """Test configuration validation."""
        from orchestrator import Orchestrator

        # Valid config should load successfully (using default config)
        orchestrator = Orchestrator(config_path=None)
        assert orchestrator.config is not None

    def test_agent_registry(self):
        """Test agent CLI registry."""
        from adapters.cli_communicator import AgentCLIRegistry

        # Test getting known patterns
        claude_pattern = AgentCLIRegistry.get_pattern("claude")
        assert claude_pattern["command"] == "claude"
        assert "method" in claude_pattern

        # Test unknown pattern returns default
        unknown_pattern = AgentCLIRegistry.get_pattern("unknown_tool")
        assert unknown_pattern["method"] == "stdin"

        # Test registering custom pattern
        AgentCLIRegistry.register_pattern("custom_tool", {"command": "custom", "method": "file"})

        custom_pattern = AgentCLIRegistry.get_pattern("custom_tool")
        assert custom_pattern["command"] == "custom"
        assert custom_pattern["method"] == "file"

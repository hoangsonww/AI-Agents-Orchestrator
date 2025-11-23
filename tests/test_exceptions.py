"""Tests for custom exceptions."""

import pytest

from orchestrator.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentTimeoutError,
    ConfigurationError,
    OrchestratorError,
    RateLimitError,
    ResourceError,
    ValidationError,
    WorkflowError,
)


class TestOrchestratorError:
    """Tests for base OrchestratorError."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = OrchestratorError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == "ORCHESTRATOR_ERROR"

    def test_error_with_details(self) -> None:
        """Test error with details."""
        details = {"key": "value", "number": 42}
        error = OrchestratorError("Test error", details=details)
        assert error.details == details

    def test_error_to_dict(self) -> None:
        """Test error serialization to dict."""
        error = OrchestratorError("Test error", error_code="TEST_ERROR", details={"foo": "bar"})
        result = error.to_dict()

        assert result["error"] == "OrchestratorError"
        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["details"] == {"foo": "bar"}


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error(self) -> None:
        """Test configuration error."""
        error = ConfigurationError("Invalid config")
        assert error.error_code == "CONFIG_ERROR"
        assert "Invalid config" in str(error)


class TestAgentNotFoundError:
    """Tests for AgentNotFoundError."""

    def test_agent_not_found_error(self) -> None:
        """Test agent not found error."""
        error = AgentNotFoundError("test-agent")
        assert error.error_code == "AGENT_NOT_FOUND"
        assert "test-agent" in str(error)
        assert error.details["agent_name"] == "test-agent"


class TestAgentExecutionError:
    """Tests for AgentExecutionError."""

    def test_agent_execution_error(self) -> None:
        """Test agent execution error."""
        error = AgentExecutionError("test-agent", "execution failed")
        assert error.error_code == "AGENT_EXECUTION_ERROR"
        assert "test-agent" in str(error)
        assert "execution failed" in str(error)


class TestAgentTimeoutError:
    """Tests for AgentTimeoutError."""

    def test_agent_timeout_error(self) -> None:
        """Test agent timeout error."""
        error = AgentTimeoutError("test-agent", 30.0)
        assert error.error_code == "AGENT_TIMEOUT"
        assert "test-agent" in str(error)
        assert "30" in str(error)
        assert error.details["timeout"] == 30.0


class TestWorkflowError:
    """Tests for WorkflowError."""

    def test_workflow_error(self) -> None:
        """Test workflow error."""
        error = WorkflowError("default", "workflow failed")
        assert error.error_code == "WORKFLOW_ERROR"
        assert "default" in str(error)
        assert "workflow failed" in str(error)


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error(self) -> None:
        """Test validation error."""
        error = ValidationError("Invalid input", field="task")
        assert error.error_code == "VALIDATION_ERROR"
        assert "Invalid input" in str(error)
        assert error.details["field"] == "task"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error(self) -> None:
        """Test rate limit error."""
        error = RateLimitError(60, 60)
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert "60" in str(error)


class TestResourceError:
    """Tests for ResourceError."""

    def test_resource_error(self) -> None:
        """Test resource error."""
        error = ResourceError("file", "Cannot access file")
        assert error.error_code == "RESOURCE_ERROR"
        assert "file" in str(error)
        assert "Cannot access file" in str(error)

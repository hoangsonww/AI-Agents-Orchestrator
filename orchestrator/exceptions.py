"""Custom exceptions for the orchestrator."""

from typing import Any, Dict, Optional


class OrchestratorError(Exception):
    """Base exception for all orchestrator errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize exception with message and optional details."""
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "ORCHESTRATOR_ERROR"
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class ConfigurationError(OrchestratorError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize configuration error."""
        super().__init__(message, error_code="CONFIG_ERROR", details=details)


class AgentNotFoundError(OrchestratorError):
    """Raised when a requested agent is not available."""

    def __init__(self, agent_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize agent not found error."""
        message = f"Agent '{agent_name}' is not available"
        super().__init__(
            message,
            error_code="AGENT_NOT_FOUND",
            details={"agent_name": agent_name, **(details or {})},
        )


class AgentExecutionError(OrchestratorError):
    """Raised when agent execution fails."""

    def __init__(
        self, agent_name: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize agent execution error."""
        full_message = f"Agent '{agent_name}' execution failed: {message}"
        super().__init__(
            full_message,
            error_code="AGENT_EXECUTION_ERROR",
            details={"agent_name": agent_name, **(details or {})},
        )


class AgentTimeoutError(OrchestratorError):
    """Raised when agent execution times out."""

    def __init__(
        self, agent_name: str, timeout: float, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize agent timeout error."""
        message = f"Agent '{agent_name}' timed out after {timeout} seconds"
        super().__init__(
            message,
            error_code="AGENT_TIMEOUT",
            details={"agent_name": agent_name, "timeout": timeout, **(details or {})},
        )


class WorkflowError(OrchestratorError):
    """Raised when workflow execution fails."""

    def __init__(
        self, workflow_name: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize workflow error."""
        full_message = f"Workflow '{workflow_name}' failed: {message}"
        super().__init__(
            full_message,
            error_code="WORKFLOW_ERROR",
            details={"workflow_name": workflow_name, **(details or {})},
        )


class ValidationError(OrchestratorError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Initialize validation error."""
        details = {"field": field} if field else {}
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class RateLimitError(OrchestratorError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, limit: int, window: int, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize rate limit error."""
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        super().__init__(
            message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window, **(details or {})},
        )


class ResourceError(OrchestratorError):
    """Raised when resource operations fail."""

    def __init__(
        self, resource_type: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize resource error."""
        full_message = f"Resource error ({resource_type}): {message}"
        super().__init__(
            full_message,
            error_code="RESOURCE_ERROR",
            details={"resource_type": resource_type, **(details or {})},
        )

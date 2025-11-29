"""Security utilities including input validation and rate limiting."""

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import RateLimitError, ValidationError


class InputValidator:
    """Input validation and sanitization."""

    # Maximum lengths
    MAX_TASK_LENGTH = 10000
    MAX_WORKFLOW_NAME_LENGTH = 100
    MAX_AGENT_NAME_LENGTH = 50
    MAX_FILE_PATH_LENGTH = 4096

    # Allowed patterns
    WORKFLOW_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
    AGENT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    # Dangerous patterns in task descriptions
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"del\s+/[FS]",
        r"format\s+[A-Z]:",
        r">\s*/dev/",
        r"curl.*\|\s*bash",
        r"wget.*\|\s*sh",
    ]

    @classmethod
    def validate_task(cls, task: str) -> str:
        """
        Validate and sanitize task description.

        Args:
            task: Task description

        Returns:
            Sanitized task

        Raises:
            ValidationError: If validation fails
        """
        if not task or not task.strip():
            raise ValidationError("Task description cannot be empty", field="task")

        if len(task) > cls.MAX_TASK_LENGTH:
            raise ValidationError(
                f"Task description exceeds maximum length of {cls.MAX_TASK_LENGTH}",
                field="task",
            )

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, task, re.IGNORECASE):
                raise ValidationError(
                    f"Task contains potentially dangerous pattern: {pattern}",
                    field="task",
                )

        return task.strip()

    @classmethod
    def validate_workflow_name(cls, name: str) -> str:
        """
        Validate workflow name.

        Args:
            name: Workflow name

        Returns:
            Validated name

        Raises:
            ValidationError: If validation fails
        """
        if not name or not name.strip():
            raise ValidationError("Workflow name cannot be empty", field="workflow")

        if len(name) > cls.MAX_WORKFLOW_NAME_LENGTH:
            raise ValidationError(
                f"Workflow name exceeds maximum length of {cls.MAX_WORKFLOW_NAME_LENGTH}",
                field="workflow",
            )

        if not cls.WORKFLOW_NAME_PATTERN.match(name):
            raise ValidationError(
                "Workflow name can only contain letters, numbers, underscores, and hyphens",
                field="workflow",
            )

        return name

    @classmethod
    def validate_agent_name(cls, name: str) -> str:
        """
        Validate agent name.

        Args:
            name: Agent name

        Returns:
            Validated name

        Raises:
            ValidationError: If validation fails
        """
        if not name or not name.strip():
            raise ValidationError("Agent name cannot be empty", field="agent")

        if len(name) > cls.MAX_AGENT_NAME_LENGTH:
            raise ValidationError(
                f"Agent name exceeds maximum length of {cls.MAX_AGENT_NAME_LENGTH}",
                field="agent",
            )

        if not cls.AGENT_NAME_PATTERN.match(name):
            raise ValidationError(
                "Agent name can only contain letters, numbers, underscores, and hyphens",
                field="agent",
            )

        return name

    @classmethod
    def validate_file_path(cls, path: str, must_exist: bool = False) -> Path:
        """
        Validate file path.

        Args:
            path: File path
            must_exist: Whether file must exist

        Returns:
            Validated Path object

        Raises:
            ValidationError: If validation fails
        """
        if not path or not path.strip():
            raise ValidationError("File path cannot be empty", field="path")

        if len(path) > cls.MAX_FILE_PATH_LENGTH:
            raise ValidationError(
                f"File path exceeds maximum length of {cls.MAX_FILE_PATH_LENGTH}",
                field="path",
            )

        # Prevent path traversal
        resolved_path = Path(path).resolve()

        if must_exist and not resolved_path.exists():
            raise ValidationError(f"File does not exist: {path}", field="path")

        return resolved_path

    @classmethod
    def validate_command(cls, command: str, allowed_commands: Optional[List[str]] = None) -> str:
        """
        Validate command.

        Args:
            command: Command to validate
            allowed_commands: List of allowed commands

        Returns:
            Validated command

        Raises:
            ValidationError: If validation fails
        """
        if not command or not command.strip():
            raise ValidationError("Command cannot be empty", field="command")

        if allowed_commands:
            if command not in allowed_commands:
                raise ValidationError(
                    f"Command '{command}' is not in allowed list: {allowed_commands}",
                    field="command",
                )

        return command


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(
        self,
        rate: int = 60,
        window: int = 60,
        capacity: Optional[int] = None,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed per window
            window: Time window in seconds
            capacity: Maximum bucket capacity (defaults to rate)
        """
        self.rate = rate
        self.window = window
        self.capacity = capacity or rate

        self.buckets: Dict[str, Dict[str, Any]] = {}

    def _get_bucket(self, key: str) -> Dict[str, Any]:
        """Get or create bucket for key."""
        if key not in self.buckets:
            self.buckets[key] = {
                "tokens": float(self.capacity),
                "last_update": time.time(),
            }
        return self.buckets[key]

    def _refill_bucket(self, bucket: Dict[str, Any]) -> None:
        """Refill bucket based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]

        # Calculate tokens to add
        tokens_to_add = (elapsed / self.window) * self.rate
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now

    def check_limit(self, key: str, tokens: int = 1) -> bool:
        """
        Check if request is within rate limit.

        Args:
            key: Identifier for rate limiting (e.g., user ID, IP address)
            tokens: Number of tokens to consume

        Returns:
            True if within limit, False otherwise

        Raises:
            RateLimitError: If rate limit exceeded
        """
        bucket = self._get_bucket(key)
        self._refill_bucket(bucket)

        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return True

        raise RateLimitError(
            limit=self.rate,
            window=self.window,
            details={"key": key, "tokens_available": bucket["tokens"]},
        )

    def get_wait_time(self, key: str, tokens: int = 1) -> float:
        """
        Get time to wait before request is allowed.

        Args:
            key: Identifier for rate limiting
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        bucket = self._get_bucket(key)
        self._refill_bucket(bucket)

        if bucket["tokens"] >= tokens:
            return 0.0

        tokens_needed = tokens - bucket["tokens"]
        return (tokens_needed / self.rate) * self.window


class SecretManager:
    """Simple secret management."""

    def __init__(self) -> None:
        """Initialize secret manager."""
        self.secrets: Dict[str, str] = {}
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load secrets from environment variables."""
        import os

        # Load common API keys
        secret_prefixes = ["API_KEY_", "SECRET_", "TOKEN_", "PASSWORD_"]

        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in secret_prefixes):
                self.secrets[key] = value

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret by key."""
        return self.secrets.get(key)

    def set_secret(self, key: str, value: str) -> None:
        """Set secret."""
        self.secrets[key] = value

    def mask_secret(self, secret: str) -> str:
        """Mask secret for logging."""
        if len(secret) <= 8:
            return "*" * len(secret)
        return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


class AuditLogger:
    """Audit logging for security events."""

    def __init__(self, log_file: Optional[Path] = None) -> None:
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
        """
        self.log_file = log_file or Path("logs/audit.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        user: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security audit event."""
        import json
        from datetime import datetime

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user": user,
            "action": action,
            "resource": resource,
            "status": status,
            "details": details or {},
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

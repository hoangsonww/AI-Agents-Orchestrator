"""Tests for security utilities."""

import pytest

from orchestrator.exceptions import RateLimitError, ValidationError
from orchestrator.security import (
    AuditLogger,
    InputValidator,
    SecretManager,
    TokenBucketRateLimiter,
)


class TestInputValidator:
    """Tests for InputValidator."""

    def test_validate_task_valid(self) -> None:
        """Test valid task validation."""
        task = "Create a REST API"
        result = InputValidator.validate_task(task)
        assert result == task

    def test_validate_task_empty(self) -> None:
        """Test empty task validation."""
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_task("")
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_task_too_long(self) -> None:
        """Test task length validation."""
        task = "a" * (InputValidator.MAX_TASK_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_task(task)
        assert "exceeds maximum length" in str(exc_info.value)

    def test_validate_task_dangerous_pattern(self) -> None:
        """Test dangerous pattern detection."""
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.validate_task("Run rm -rf /")
        assert "dangerous pattern" in str(exc_info.value)

    def test_validate_workflow_name_valid(self) -> None:
        """Test valid workflow name."""
        name = "my-workflow_123"
        result = InputValidator.validate_workflow_name(name)
        assert result == name

    def test_validate_workflow_name_invalid(self) -> None:
        """Test invalid workflow name."""
        with pytest.raises(ValidationError):
            InputValidator.validate_workflow_name("my workflow!")

    def test_validate_agent_name_valid(self) -> None:
        """Test valid agent name."""
        name = "claude-agent"
        result = InputValidator.validate_agent_name(name)
        assert result == name

    def test_validate_command_allowed(self) -> None:
        """Test command validation with allowed list."""
        result = InputValidator.validate_command("claude", ["claude", "codex"])
        assert result == "claude"

    def test_validate_command_not_allowed(self) -> None:
        """Test command validation with disallowed command."""
        with pytest.raises(ValidationError):
            InputValidator.validate_command("dangerous", ["claude", "codex"])


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    def test_rate_limiter_allows_request(self) -> None:
        """Test rate limiter allows request within limit."""
        limiter = TokenBucketRateLimiter(rate=10, window=60)
        assert limiter.check_limit("test-key")

    def test_rate_limiter_blocks_request(self) -> None:
        """Test rate limiter blocks request exceeding limit."""
        limiter = TokenBucketRateLimiter(rate=2, window=60, capacity=2)

        # First two requests should succeed
        assert limiter.check_limit("test-key")
        assert limiter.check_limit("test-key")

        # Third request should fail
        with pytest.raises(RateLimitError):
            limiter.check_limit("test-key")

    def test_rate_limiter_wait_time(self) -> None:
        """Test rate limiter wait time calculation."""
        limiter = TokenBucketRateLimiter(rate=1, window=1, capacity=1)
        limiter.check_limit("test-key")

        wait_time = limiter.get_wait_time("test-key")
        assert wait_time > 0


class TestSecretManager:
    """Tests for SecretManager."""

    def test_set_and_get_secret(self) -> None:
        """Test setting and getting secrets."""
        manager = SecretManager()
        manager.set_secret("test_key", "test_value")
        assert manager.get_secret("test_key") == "test_value"

    def test_get_nonexistent_secret(self) -> None:
        """Test getting nonexistent secret."""
        manager = SecretManager()
        assert manager.get_secret("nonexistent") is None

    def test_mask_secret(self) -> None:
        """Test secret masking."""
        manager = SecretManager()
        masked = manager.mask_secret("my-secret-api-key-12345")
        assert masked.startswith("my-s")
        assert masked.endswith("2345")
        assert "*" in masked


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_log_event(self, tmp_path) -> None:
        """Test logging audit event."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log_event(
            event_type="test_event",
            user="test_user",
            action="test_action",
            status="success",
        )

        assert log_file.exists()
        content = log_file.read_text()
        assert "test_event" in content
        assert "test_user" in content
        assert "test_action" in content

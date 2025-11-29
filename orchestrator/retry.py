"""Retry logic and resilience patterns for the orchestrator."""

import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from tenacity import (
    RetryCallState,
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from .exceptions import AgentExecutionError, AgentTimeoutError

T = TypeVar("T")

logger = logging.getLogger(__name__)


def retry_on_error(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry function on error.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Base wait time between retries
        exponential_backoff: Use exponential backoff if True, fixed wait if False
        exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    wait_strategy = (
        wait_exponential(multiplier=wait_seconds, min=wait_seconds, max=60)
        if exponential_backoff
        else wait_fixed(wait_seconds)
    )

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )


def retry_agent_execution(
    max_attempts: int = 3,
    wait_seconds: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Specialized retry decorator for agent execution.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Base wait time between retries

    Returns:
        Decorated function with retry logic
    """
    return retry_on_error(
        max_attempts=max_attempts,
        wait_seconds=wait_seconds,
        exponential_backoff=True,
        exceptions=(AgentExecutionError, AgentTimeoutError, ConnectionError, TimeoutError),
    )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for resilience.

    Prevents cascading failures by stopping calls to a service
    that is likely to fail.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function execution

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"Retry after {self.recovery_timeout}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "closed"
        logger.info("Circuit breaker: Reset to CLOSED state")

    def _on_failure(self) -> None:
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(
                f"Circuit breaker: Opened after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout}s"
            )


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to apply circuit breaker pattern.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time in seconds before attempting recovery
        expected_exception: Exception type to catch

    Returns:
        Decorated function with circuit breaker
    """
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int) -> None:
        """
        Initialize rate limiter.

        Args:
            rate: Number of tokens added per second
            capacity: Maximum number of tokens
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()

    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        now = time.time()
        elapsed = now - self.last_update

        # Add new tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens to wait for
        """
        while not self.acquire(tokens):
            time.sleep(0.1)

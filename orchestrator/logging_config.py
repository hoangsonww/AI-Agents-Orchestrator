"""Structured logging configuration for the orchestrator."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = False,
    enable_colors: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        json_logs: Output logs in JSON format
        enable_colors: Enable colored console output
    """
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable output for development
        processors.append(
            structlog.dev.ConsoleRenderer(colors=enable_colors)
            if enable_colors
            else structlog.processors.KeyValueRenderer()
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handlers = []

    # Console handler with Rich
    if enable_colors:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
        )
    else:
        console_handler = logging.StreamHandler(sys.stderr)

    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file

        if json_logs:
            formatter = logging.Formatter("%(message)s")
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=handlers,
        format="%(message)s",
    )

    # Set levels for noisy third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding temporary context to logs."""

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize log context.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs

    def __enter__(self) -> "LogContext":
        """Enter context."""
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context."""
        structlog.contextvars.clear_contextvars()


def log_execution(
    logger: Optional[structlog.stdlib.BoundLogger] = None,
) -> Any:
    """
    Decorator to log function execution.

    Args:
        logger: Logger instance (optional)

    Returns:
        Decorated function
    """

    def decorator(func: Any) -> Any:
        import functools

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            logger.info(
                "function_called",
                function=func.__name__,
                args=args,
                kwargs=kwargs,
            )

            try:
                result = func(*args, **kwargs)
                logger.info("function_completed", function=func.__name__)
                return result
            except Exception as e:
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    error=str(e),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


class PerformanceLogger:
    """Performance monitoring and logging."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, operation: str) -> None:
        """
        Initialize performance logger.

        Args:
            logger: Logger instance
            operation: Name of the operation being measured
        """
        self.logger = logger
        self.operation = operation
        self.start_time: Optional[float] = None

    def __enter__(self) -> "PerformanceLogger":
        """Start performance measurement."""
        import time

        self.start_time = time.time()
        self.logger.debug("operation_started", operation=self.operation)
        return self

    def __exit__(self, *args: Any) -> None:
        """End performance measurement."""
        import time

        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.logger.info(
                "operation_completed",
                operation=self.operation,
                duration_seconds=round(duration, 3),
            )

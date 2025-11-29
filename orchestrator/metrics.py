"""Metrics collection and monitoring for the orchestrator."""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)


class MetricsCollector:
    """Centralized metrics collection."""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        """
        Initialize metrics collector.

        Args:
            registry: Prometheus registry (optional)
        """
        self.registry = registry or CollectorRegistry()

        # Application info
        self.app_info = Info(
            "orchestrator_app",
            "Application information",
            registry=self.registry,
        )
        self.app_info.info({"version": "1.0.0", "name": "ai-orchestrator"})

        # Task metrics
        self.tasks_total = Counter(
            "orchestrator_tasks_total",
            "Total number of tasks executed",
            ["workflow", "status"],
            registry=self.registry,
        )

        self.tasks_in_progress = Gauge(
            "orchestrator_tasks_in_progress",
            "Number of tasks currently in progress",
            registry=self.registry,
        )

        self.task_duration = Histogram(
            "orchestrator_task_duration_seconds",
            "Task execution duration in seconds",
            ["workflow"],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800],
            registry=self.registry,
        )

        # Agent metrics
        self.agent_calls_total = Counter(
            "orchestrator_agent_calls_total",
            "Total number of agent calls",
            ["agent", "status"],
            registry=self.registry,
        )

        self.agent_duration = Histogram(
            "orchestrator_agent_duration_seconds",
            "Agent execution duration in seconds",
            ["agent"],
            buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
            registry=self.registry,
        )

        self.agent_errors = Counter(
            "orchestrator_agent_errors_total",
            "Total number of agent errors",
            ["agent", "error_type"],
            registry=self.registry,
        )

        # Workflow metrics
        self.workflow_iterations = Summary(
            "orchestrator_workflow_iterations",
            "Number of iterations per workflow",
            ["workflow"],
            registry=self.registry,
        )

        self.workflow_success_rate = Gauge(
            "orchestrator_workflow_success_rate",
            "Workflow success rate",
            ["workflow"],
            registry=self.registry,
        )

        # System metrics
        self.active_agents = Gauge(
            "orchestrator_active_agents",
            "Number of active agents",
            registry=self.registry,
        )

        # Cache metrics
        self.cache_hits = Counter(
            "orchestrator_cache_hits_total",
            "Total number of cache hits",
            registry=self.registry,
        )

        self.cache_misses = Counter(
            "orchestrator_cache_misses_total",
            "Total number of cache misses",
            registry=self.registry,
        )

    def record_task_start(self, workflow: str) -> None:
        """Record task start."""
        self.tasks_in_progress.inc()

    def record_task_complete(self, workflow: str, success: bool, duration: float) -> None:
        """Record task completion."""
        status = "success" if success else "failure"
        self.tasks_total.labels(workflow=workflow, status=status).inc()
        self.tasks_in_progress.dec()
        self.task_duration.labels(workflow=workflow).observe(duration)

    def record_agent_call(
        self, agent: str, success: bool, duration: float, error_type: Optional[str] = None
    ) -> None:
        """Record agent call."""
        status = "success" if success else "failure"
        self.agent_calls_total.labels(agent=agent, status=status).inc()
        self.agent_duration.labels(agent=agent).observe(duration)

        if not success and error_type:
            self.agent_errors.labels(agent=agent, error_type=error_type).inc()

    def record_workflow_iterations(self, workflow: str, iterations: int) -> None:
        """Record workflow iterations."""
        self.workflow_iterations.labels(workflow=workflow).observe(iterations)

    def update_active_agents(self, count: int) -> None:
        """Update active agents count."""
        self.active_agents.set(count)

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits.inc()

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.cache_misses.inc()

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get metrics content type."""
        return CONTENT_TYPE_LATEST


# Global metrics instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def track_execution_time(metric_name: str, labels: Optional[Dict[str, str]] = None) -> Callable:
    """
    Decorator to track execution time.

    Args:
        metric_name: Name of the metric
        labels: Optional labels for the metric

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Record metric (implementation depends on metric type)

        return wrapper

    return decorator


def track_task_execution(workflow: str) -> Callable:
    """
    Decorator to track task execution.

    Args:
        workflow: Workflow name

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            metrics = get_metrics_collector()
            metrics.record_task_start(workflow)

            start_time = time.time()
            success = False

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                duration = time.time() - start_time
                metrics.record_task_complete(workflow, success, duration)

        return wrapper

    return decorator

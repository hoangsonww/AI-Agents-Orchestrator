"""Health checks and readiness probes for production deployment."""

import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0


class HealthChecker:
    """Performs health checks for the orchestrator."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self.checks: List[Any] = [
            self._check_python_version,
            self._check_disk_space,
            self._check_memory,
            self._check_config_file,
            self._check_directories,
            self._check_dependencies,
        ]

    def _check_python_version(self) -> HealthCheckResult:
        """Check Python version."""
        import sys

        start = time.time()
        try:
            version = sys.version_info
            if version.major == 3 and version.minor >= 8:
                status = HealthStatus.HEALTHY
                message = f"Python {version.major}.{version.minor}.{version.micro}"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Python version {version.major}.{version.minor} < 3.8"

            return HealthCheckResult(
                name="python_version",
                status=status,
                message=message,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name="python_version",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking Python version: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        start = time.time()
        try:
            import shutil

            stat = shutil.disk_usage(".")
            free_gb = stat.free / (1024**3)

            if free_gb > 5:
                status = HealthStatus.HEALTHY
                message = f"{free_gb:.2f} GB free"
            elif free_gb > 1:
                status = HealthStatus.DEGRADED
                message = f"Low disk space: {free_gb:.2f} GB free"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk space: {free_gb:.2f} GB free"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={"free_gb": round(free_gb, 2)},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking disk space: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def _check_memory(self) -> HealthCheckResult:
        """Check available memory."""
        start = time.time()
        try:
            import psutil

            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)

            if memory.percent < 80:
                status = HealthStatus.HEALTHY
                message = f"{available_gb:.2f} GB available ({memory.percent:.1f}% used)"
            elif memory.percent < 90:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {memory.percent:.1f}%"

            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                details={"available_gb": round(available_gb, 2), "percent_used": memory.percent},
                duration_ms=(time.time() - start) * 1000,
            )
        except ImportError:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="psutil not installed - memory check skipped",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking memory: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def _check_config_file(self) -> HealthCheckResult:
        """Check configuration file."""
        start = time.time()
        try:
            config_path = Path("config/agents.yaml")

            if config_path.exists():
                import yaml

                with open(config_path) as f:
                    config = yaml.safe_load(f)

                if config and "agents" in config and "workflows" in config:
                    status = HealthStatus.HEALTHY
                    message = "Configuration valid"
                else:
                    status = HealthStatus.DEGRADED
                    message = "Configuration missing required sections"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Configuration file not found"

            return HealthCheckResult(
                name="config_file",
                status=status,
                message=message,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name="config_file",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking config: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def _check_directories(self) -> HealthCheckResult:
        """Check required directories."""
        start = time.time()
        try:
            required_dirs = ["output", "workspace", "reports", "sessions", "logs"]
            missing_dirs = []

            for dir_name in required_dirs:
                path = Path(dir_name)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    missing_dirs.append(dir_name)

            if not missing_dirs:
                status = HealthStatus.HEALTHY
                message = "All required directories exist"
            else:
                status = HealthStatus.DEGRADED
                message = f"Missing directories: {', '.join(missing_dirs)}"

            return HealthCheckResult(
                name="directories",
                status=status,
                message=message,
                details={"missing": missing_dirs},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name="directories",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking directories: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def _check_dependencies(self) -> HealthCheckResult:
        """Check required dependencies."""
        start = time.time()
        try:
            required = ["click", "pyyaml", "rich", "pydantic"]
            missing = []

            for package in required:
                try:
                    __import__(package)
                except ImportError:
                    missing.append(package)

            if not missing:
                status = HealthStatus.HEALTHY
                message = "All required dependencies installed"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Missing dependencies: {', '.join(missing)}"

            return HealthCheckResult(
                name="dependencies",
                status=status,
                message=message,
                details={"missing": missing},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name="dependencies",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking dependencies: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_agent_availability(self, agent_name: str, command: str) -> HealthCheckResult:
        """Check if an agent is available."""
        start = time.time()
        try:
            # Check if command exists
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                status = HealthStatus.HEALTHY
                message = f"Agent {agent_name} available at {result.stdout.strip()}"
            else:
                status = HealthStatus.DEGRADED
                message = f"Agent {agent_name} command '{command}' not found"

            return HealthCheckResult(
                name=f"agent_{agent_name}",
                status=status,
                message=message,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name=f"agent_{agent_name}",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking agent: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = []
        start_time = time.time()

        for check in self.checks:
            result = check()
            results.append(result)

        # Determine overall status
        statuses = [r.status for r in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "duration_ms": (time.time() - start_time) * 1000,
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }

    def is_ready(self) -> bool:
        """Check if the orchestrator is ready to accept requests."""
        health = self.run_all_checks()
        return health["status"] in [HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value]

    def is_alive(self) -> bool:
        """Check if the orchestrator is alive (basic liveness check)."""
        return True  # If we can run this method, we're alive

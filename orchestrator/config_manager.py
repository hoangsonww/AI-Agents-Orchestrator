"""Configuration management with environment variables and validation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    """Configuration for an individual agent."""

    enabled: bool = True
    command: str
    role: str
    timeout: int = 300
    max_retries: int = 3
    description: str = ""

    model_config = SettingsConfigDict(extra="allow")


class WorkflowSettings(BaseSettings):
    """Workflow execution settings."""

    default_workflow: str = "default"
    max_iterations: int = 3
    max_retries: int = 3
    retry_delay: float = 1.0
    min_suggestions_threshold: int = 3

    model_config = SettingsConfigDict(extra="allow")


class DirectorySettings(BaseSettings):
    """Directory configuration."""

    output_dir: Path = Field(default=Path("./output"))
    workspace_dir: Path = Field(default=Path("./workspace"))
    reports_dir: Path = Field(default=Path("./reports"))
    sessions_dir: Path = Field(default=Path("./sessions"))
    logs_dir: Path = Field(default=Path("./logs"))

    @field_validator("*", mode="before")
    @classmethod
    def create_directories(cls, v: Any) -> Path:
        """Ensure directories exist."""
        if isinstance(v, (str, Path)):
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return v

    model_config = SettingsConfigDict(extra="allow")


class PerformanceSettings(BaseSettings):
    """Performance and optimization settings."""

    enable_caching: bool = True
    cache_ttl: int = 3600
    max_concurrent_agents: int = 3
    request_timeout: int = 600
    enable_async_execution: bool = True

    model_config = SettingsConfigDict(extra="allow")


class MonitoringSettings(BaseSettings):
    """Monitoring and metrics settings."""

    enable_metrics: bool = True
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    enable_distributed_tracing: bool = False

    model_config = SettingsConfigDict(extra="allow")


class SecuritySettings(BaseSettings):
    """Security settings."""

    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 60
    max_task_length: int = 10000
    allowed_commands: List[str] = Field(
        default_factory=lambda: ["codex", "gemini", "claude", "copilot"]
    )

    model_config = SettingsConfigDict(extra="allow")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    log_level: str = "INFO"
    log_file: Optional[str] = "logs/ai-orchestrator.log"
    json_logs: bool = False
    enable_colors: bool = True

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(extra="allow")


class AppSettings(BaseSettings):
    """Application settings loaded from environment."""

    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    # Nested settings
    workflow: WorkflowSettings = Field(default_factory=WorkflowSettings)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env.lower() == "development"


class ConfigManager:
    """Centralized configuration management."""

    def __init__(self, config_file: Optional[Path] = None, env_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to YAML config file
            env_file: Path to .env file
        """
        self.config_file = config_file
        self.env_file = env_file

        # Load environment variables
        if env_file and env_file.exists():
            from dotenv import load_dotenv

            load_dotenv(env_file)

        # Load app settings
        self.settings = AppSettings()

        # Load YAML configuration
        self.yaml_config: Dict[str, Any] = {}
        if config_file and config_file.exists():
            import yaml

            with open(config_file, "r") as f:
                self.yaml_config = yaml.safe_load(f) or {}

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration dictionary or None
        """
        agents = self.yaml_config.get("agents", {})
        return agents.get(agent_name)

    def get_workflow_config(self, workflow_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get configuration for a specific workflow.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Workflow configuration list or None
        """
        workflows = self.yaml_config.get("workflows", {})
        return workflows.get(workflow_name)

    def get_all_agents(self) -> Dict[str, Any]:
        """Get all agent configurations."""
        return self.yaml_config.get("agents", {})

    def get_all_workflows(self) -> Dict[str, Any]:
        """Get all workflow configurations."""
        return self.yaml_config.get("workflows", {})

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key (supports dot notation)
            default: Default value if not found

        Returns:
            Setting value or default
        """
        # Try YAML config first
        keys = key.split(".")
        value = self.yaml_config.get("settings", {})

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        if value is not None:
            return value

        # Fall back to environment settings
        return getattr(self.settings, key, default)

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if valid, False otherwise
        """
        # Check required sections
        required_sections = ["agents", "workflows"]
        for section in required_sections:
            if section not in self.yaml_config:
                return False

        # Validate at least one agent is enabled
        agents = self.get_all_agents()
        if not any(agent.get("enabled", True) for agent in agents.values()):
            return False

        # Validate at least one workflow exists
        workflows = self.get_all_workflows()
        if not workflows:
            return False

        return True


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def init_config(config_file: Optional[Path] = None, env_file: Optional[Path] = None) -> ConfigManager:
    """Initialize configuration manager."""
    global _config_manager
    _config_manager = ConfigManager(config_file=config_file, env_file=env_file)
    return _config_manager

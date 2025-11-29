"""
Pytest configuration and fixtures
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    workspace = tempfile.mkdtemp(prefix="test_workspace_")
    yield workspace
    # Cleanup
    if os.path.exists(workspace):
        shutil.rmtree(workspace)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "agents": {
            "test_agent": {"enabled": True, "command": "echo", "role": "test", "timeout": 30}
        },
        "workflows": {"test_workflow": [{"agent": "test_agent", "task": "test"}]},
        "settings": {"max_iterations": 2, "output_dir": "./test_output", "log_level": "DEBUG"},
    }


@pytest.fixture
def mock_cli_response():
    """Mock CLI response for testing."""
    return {"stdout": "Test output", "stderr": "", "returncode": 0}

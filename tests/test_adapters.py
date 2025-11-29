"""
Tests for AI agent adapters
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from adapters import (
    AgentCapability,
    AgentResponse,
    BaseAdapter,
    ClaudeAdapter,
    CodexAdapter,
    CopilotAdapter,
    GeminiAdapter,
)


class TestBaseAdapter:
    """Test BaseAdapter functionality."""

    def test_initialization(self):
        """Test adapter initialization."""
        config = {"name": "test_adapter", "command": "test_command", "enabled": True, "timeout": 60}

        class TestAdapter(BaseAdapter):
            def get_capabilities(self):
                return [AgentCapability.IMPLEMENTATION]

            def execute_task(self, task, context):
                return AgentResponse(success=True, output="test")

        adapter = TestAdapter(config)

        assert adapter.name == "test_adapter"
        assert adapter.command == "test_command"
        assert adapter.enabled is True
        assert adapter.timeout == 60

    @patch("subprocess.run")
    def test_is_available(self, mock_run):
        """Test checking if an agent is available."""
        config = {"name": "test", "command": "test_cmd", "enabled": True}

        class TestAdapter(BaseAdapter):
            def get_capabilities(self):
                return []

            def execute_task(self, task, context):
                return AgentResponse(success=True, output="")

        adapter = TestAdapter(config)

        # Mock successful command check
        mock_run.return_value = Mock(returncode=0)
        assert adapter.is_available() is True

        # Mock failed command check
        mock_run.return_value = Mock(returncode=1)
        assert adapter.is_available() is False

    def test_format_task_prompt(self):
        """Test task prompt formatting."""
        config = {"name": "test", "command": "test", "enabled": True}

        class TestAdapter(BaseAdapter):
            def get_capabilities(self):
                return []

            def execute_task(self, task, context):
                return AgentResponse(success=True, output="")

        adapter = TestAdapter(config)

        task = "Implement feature X"
        context = {"previous_output": "Previous work", "feedback": "Fix this issue"}

        prompt = adapter.format_task_prompt(task, context)

        assert task in prompt
        assert "Previous work" in prompt
        assert "Fix this issue" in prompt


class TestClaudeAdapter:
    """Test Claude adapter."""

    def test_capabilities(self):
        """Test Claude capabilities."""
        config = {"name": "claude", "command": "claude", "enabled": True}
        adapter = ClaudeAdapter(config)

        capabilities = adapter.get_capabilities()

        assert AgentCapability.IMPLEMENTATION in capabilities
        assert AgentCapability.REFACTORING in capabilities
        assert AgentCapability.CODE_REVIEW in capabilities

    def test_build_claude_prompt(self):
        """Test Claude prompt building."""
        config = {"name": "claude", "command": "claude", "enabled": True}
        adapter = ClaudeAdapter(config)

        task = "Refactor this code"
        context = {
            "role": "refine",
            "feedback": "Improve error handling",
            "implementation": "def foo(): pass",
        }

        prompt = adapter._build_claude_prompt(task, context)

        assert "refining code" in prompt.lower()
        assert "Improve error handling" in prompt
        assert "def foo(): pass" in prompt


class TestCodexAdapter:
    """Test Codex adapter."""

    def test_capabilities(self):
        """Test Codex capabilities."""
        config = {"name": "codex", "command": "codex", "enabled": True}
        adapter = CodexAdapter(config)

        capabilities = adapter.get_capabilities()

        assert AgentCapability.IMPLEMENTATION in capabilities
        assert AgentCapability.TESTING in capabilities

    def test_build_codex_prompt(self):
        """Test Codex prompt building."""
        config = {"name": "codex", "command": "codex", "enabled": True}
        adapter = CodexAdapter(config)

        task = "Create a REST API"
        context = {"language": "Python", "framework": "Flask"}

        prompt = adapter._build_codex_prompt(task, context)

        assert "Create a REST API" in prompt
        assert "Python" in prompt
        assert "Flask" in prompt


class TestGeminiAdapter:
    """Test Gemini adapter."""

    def test_capabilities(self):
        """Test Gemini capabilities."""
        config = {"name": "gemini", "command": "gemini-cli", "enabled": True}
        adapter = GeminiAdapter(config)

        capabilities = adapter.get_capabilities()

        assert AgentCapability.CODE_REVIEW in capabilities
        assert AgentCapability.ARCHITECTURE in capabilities

    def test_build_review_prompt(self):
        """Test Gemini review prompt building."""
        config = {"name": "gemini", "command": "gemini-cli", "enabled": True}
        adapter = GeminiAdapter(config)

        task = "Review this code"
        context = {"implementation": "def bar(): return 42"}

        prompt = adapter._build_review_prompt(task, context)

        assert "expert code reviewer" in prompt.lower()
        assert "SOLID" in prompt
        assert "def bar(): return 42" in prompt

    def test_parse_review_feedback(self):
        """Test parsing review feedback."""
        config = {"name": "gemini", "command": "gemini-cli", "enabled": True}
        adapter = GeminiAdapter(config)

        output = """
        Here are my suggestions:

        1. Improve error handling
        2. Add input validation
        - Use type hints
        - Add docstrings

        Critical: Security vulnerability detected
        """

        suggestions = adapter._parse_review_feedback(output)

        assert len(suggestions) > 0
        assert any("error handling" in s.lower() for s in suggestions)
        assert any("Critical" in s for s in suggestions)


class TestCopilotAdapter:
    """Test Copilot adapter."""

    def test_capabilities(self):
        """Test Copilot capabilities."""
        config = {"name": "copilot", "command": "gh", "enabled": True}
        adapter = CopilotAdapter(config)

        capabilities = adapter.get_capabilities()

        assert AgentCapability.IMPLEMENTATION in capabilities

    def test_extract_suggestions(self):
        """Test extracting Copilot suggestions."""
        config = {"name": "copilot", "command": "gh", "enabled": True}
        adapter = CopilotAdapter(config)

        output = """
        Here are some suggestions:

        1. Use async/await
        Implementation details here

        2. Add caching layer
        More details

        3. Optimize database queries
        """

        suggestions = adapter._extract_copilot_suggestions(output)

        assert len(suggestions) > 0


class TestAgentResponse:
    """Test AgentResponse dataclass."""

    def test_basic_response(self):
        """Test basic response creation."""
        response = AgentResponse(success=True, output="Test output")

        assert response.success is True
        assert response.output == "Test output"
        assert response.error is None
        assert response.files_modified == []
        assert response.suggestions == []

    def test_response_with_data(self):
        """Test response with additional data."""
        response = AgentResponse(
            success=True,
            output="Output",
            files_modified=["file1.py", "file2.py"],
            suggestions=["Suggestion 1", "Suggestion 2"],
            metadata={"key": "value"},
        )

        assert len(response.files_modified) == 2
        assert len(response.suggestions) == 2
        assert response.metadata["key"] == "value"

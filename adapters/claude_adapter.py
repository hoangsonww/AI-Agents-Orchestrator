"""Adapter for Claude Code CLI."""

from typing import Any, Dict, List

from .base import AgentCapability, AgentResponse, BaseAdapter


class ClaudeAdapter(BaseAdapter):
    """Adapter for interacting with Claude Code CLI."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the Claude adapter."""
        super().__init__(config)
        self.command = config.get("command", "claude")

    def get_capabilities(self) -> List[AgentCapability]:
        """Return the capabilities of the Claude agent."""
        return [
            AgentCapability.IMPLEMENTATION,
            AgentCapability.REFACTORING,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.DOCUMENTATION,
        ]

    def execute_task(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """Execute a task using Claude Code.

        Claude Code can work with files in the current directory.
        We'll use it to refine code based on feedback.
        """
        prompt = self._build_claude_prompt(task, context)

        # Get working directory from context
        working_dir = context.get("working_dir", "./workspace")

        # Use the enhanced communication method
        response = self._run_command_with_prompt(
            prompt=prompt, working_dir=working_dir, use_workspace=True
        )

        # Parse Claude's response to extract suggestions
        if response.success:
            suggestions = self._extract_suggestions(response.output)
            response.suggestions = suggestions

        # Files are already tracked by the workspace monitor
        return response

    def _build_claude_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a detailed prompt for Claude."""
        parts = []

        if context.get("role") == "refine":
            parts.append("You are refining code based on review feedback.")
            parts.append(f"\nTask: {task}")

            if context.get("feedback"):
                parts.append("\n\nCode Review Feedback:")
                parts.append(context["feedback"])

            if context.get("implementation"):
                parts.append("\n\nCurrent Implementation:")
                parts.append(context["implementation"])

            parts.append(
                "\n\nPlease implement the suggested improvements while maintaining code functionality."
            )
            parts.append("Focus on SOLID principles, clean code, and best practices.")

        else:
            # General implementation
            parts.append(f"Task: {task}")

            if context.get("requirements"):
                parts.append(f"\n\nRequirements:\n{context['requirements']}")

        parts.append("\n\nPlease provide clear, well-documented code with proper error handling.")

        return "\n".join(parts)

    def _extract_modified_files(self, output: str, context: Dict[str, Any]) -> List[str]:
        """Extract list of files that were modified from Claude's output."""
        files = []

        # Look for common patterns in output
        for line in output.split("\n"):
            # Pattern: "Modified: path/to/file.py"
            if "modified:" in line.lower() or "created:" in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    files.append(parts[1].strip())

        # Also check context for file hints
        if context.get("files"):
            files.extend(context["files"])

        return list(set(files))  # Remove duplicates

    def _extract_suggestions(self, output: str) -> List[str]:
        """Extract suggestions from Claude's output."""
        suggestions = []

        # Look for suggestion markers
        in_suggestions = False
        for line in output.split("\n"):
            if "suggestion" in line.lower() or "recommendation" in line.lower():
                in_suggestions = True
            elif in_suggestions and line.strip().startswith("-"):
                suggestions.append(line.strip()[1:].strip())
            elif in_suggestions and not line.strip():
                in_suggestions = False

        return suggestions

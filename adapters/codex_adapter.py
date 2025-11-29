"""Adapter for OpenAI Codex CLI."""

from typing import Any, Dict, List

from .base import AgentCapability, AgentResponse, BaseAdapter


class CodexAdapter(BaseAdapter):
    """Adapter for interacting with OpenAI Codex CLI."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the Codex adapter."""
        super().__init__(config)
        self.command = config.get("command", "codex")

    def get_capabilities(self) -> List[AgentCapability]:
        """Return the capabilities of the Codex agent."""
        return [
            AgentCapability.IMPLEMENTATION,
            AgentCapability.TESTING,
            AgentCapability.DEBUGGING,
        ]

    def execute_task(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """Execute a task using Codex.

        Codex is typically used for initial implementation.
        """
        prompt = self._build_codex_prompt(task, context)

        # Get working directory from context
        working_dir = context.get("working_dir", "./workspace")

        # Use the enhanced communication method
        response = self._run_command_with_prompt(
            prompt=prompt, working_dir=working_dir, use_workspace=True
        )

        # Files are tracked by workspace monitor
        return response

    def _build_codex_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a detailed prompt for Codex."""
        parts = []

        parts.append(f"Task: {task}")

        if context.get("language"):
            parts.append(f"\nLanguage: {context['language']}")

        if context.get("framework"):
            parts.append(f"Framework: {context['framework']}")

        parts.append("\n\nRequirements:")
        parts.append("- Write clean, production-ready code")
        parts.append("- Include comprehensive error handling")
        parts.append("- Add docstrings and comments")
        parts.append("- Follow best practices and design patterns")
        parts.append("- Ensure code is testable")

        if context.get("additional_requirements"):
            for req in context["additional_requirements"]:
                parts.append(f"- {req}")

        parts.append("\n\nPlease implement a complete, working solution.")

        return "\n".join(parts)

    def _extract_generated_files(self, output: str, context: Dict[str, Any]) -> List[str]:
        """Extract list of files that were generated."""
        files = []

        # Look for file creation patterns
        for line in output.split("\n"):
            if "created:" in line.lower() or "generated:" in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    files.append(parts[1].strip())

            # Look for file path patterns
            if line.strip().endswith((".py", ".js", ".ts", ".java", ".go", ".rs")):
                files.append(line.strip())

        return files

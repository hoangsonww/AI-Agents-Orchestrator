"""
Adapter for GitHub Copilot CLI.
"""

from typing import Any, Dict, List

from .base import AgentCapability, AgentResponse, BaseAdapter


class CopilotAdapter(BaseAdapter):
    """Adapter for interacting with GitHub Copilot CLI."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.command = config.get("command", "github-copilot-cli")

    def get_capabilities(self) -> List[AgentCapability]:
        """Copilot provides suggestions and helps with implementation."""
        return [
            AgentCapability.IMPLEMENTATION,
            AgentCapability.DEBUGGING,
            AgentCapability.TESTING,
        ]

    def execute_task(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a task using GitHub Copilot CLI.

        Copilot is useful for getting suggestions and alternative implementations.
        """
        prompt = self._build_copilot_prompt(task, context)

        # Copilot typically provides suggestions, not direct modifications
        working_dir = context.get("working_dir", None)

        # Use the enhanced communication method
        response = self._run_command_with_prompt(
            prompt=prompt, working_dir=working_dir, use_workspace=False
        )

        if response.success:
            # Extract suggestions
            suggestions = self._extract_copilot_suggestions(response.output)
            response.suggestions = suggestions

        return response

    def _build_copilot_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a prompt for Copilot."""
        parts = [task]

        if context.get("code_context"):
            parts.append(f"\n\nContext:\n{context['code_context']}")

        if context.get("language"):
            parts.append(f"\n\nLanguage: {context['language']}")

        return "\n".join(parts)

    def _extract_copilot_suggestions(self, output: str) -> List[str]:
        """Extract suggestions from Copilot's output."""
        suggestions = []

        # Copilot often provides multiple numbered suggestions
        current_suggestion: List[str] = []
        for line in output.split("\n"):
            if line.strip().startswith(("1.", "2.", "3.", "4.", "5.")):
                if current_suggestion:
                    suggestions.append("\n".join(current_suggestion))
                    current_suggestion = []
                current_suggestion.append(line.strip())
            elif current_suggestion:
                current_suggestion.append(line.strip())

        if current_suggestion:
            suggestions.append("\n".join(current_suggestion))

        return suggestions if suggestions else [output]

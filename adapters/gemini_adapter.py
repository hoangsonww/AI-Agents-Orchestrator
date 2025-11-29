"""
Adapter for Google Gemini CLI.
"""

import re
from typing import Any, Dict, List

from .base import AgentCapability, AgentResponse, BaseAdapter


class GeminiAdapter(BaseAdapter):
    """Adapter for interacting with Google Gemini CLI."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.command = config.get("command", "gemini-cli")

    def get_capabilities(self) -> List[AgentCapability]:
        """Gemini is excellent for code review and architecture analysis."""
        return [
            AgentCapability.CODE_REVIEW,
            AgentCapability.ARCHITECTURE,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
        ]

    def execute_task(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a code review task using Gemini.

        Gemini is primarily used for reviewing code and providing feedback.
        """
        prompt = self._build_review_prompt(task, context)

        # Gemini typically doesn't work in a workspace, so use standard execution
        working_dir = context.get("working_dir", None)

        # Use the enhanced communication method
        response = self._run_command_with_prompt(
            prompt=prompt,
            working_dir=working_dir,
            use_workspace=False,  # Gemini does review, not file modification
        )

        if response.success:
            # Parse review feedback
            suggestions = self._parse_review_feedback(response.output)
            response.suggestions = suggestions

            # Extract mentioned files
            files = self._extract_mentioned_files(response.output, context)
            if files:
                response.files_modified = files

        return response

    def _build_review_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a detailed code review prompt for Gemini."""
        parts = []

        parts.append("You are an expert code reviewer. Please analyze the following code.")
        parts.append(f"\nTask: {task}")

        if context.get("implementation"):
            parts.append("\n\nCode to Review:")
            parts.append("```")
            parts.append(context["implementation"])
            parts.append("```")

        parts.append("\n\nPlease review this code focusing on:")
        parts.append("\n**SOLID Principles:**")
        parts.append("- Single Responsibility Principle")
        parts.append("- Open/Closed Principle")
        parts.append("- Liskov Substitution Principle")
        parts.append("- Interface Segregation Principle")
        parts.append("- Dependency Inversion Principle")

        parts.append("\n**Code Quality:**")
        parts.append("- Design patterns and architectural decisions")
        parts.append("- Error handling and edge cases")
        parts.append("- Performance considerations")
        parts.append("- Security vulnerabilities")
        parts.append("- Code readability and maintainability")
        parts.append("- Test coverage and testability")

        parts.append("\n**Best Practices:**")
        parts.append("- Naming conventions")
        parts.append("- Documentation and comments")
        parts.append("- Code organization")
        parts.append("- DRY (Don't Repeat Yourself)")
        parts.append("- KISS (Keep It Simple, Stupid)")

        parts.append("\n\nProvide specific, actionable feedback with examples.")
        parts.append("Prioritize issues by severity: Critical, High, Medium, Low.")

        return "\n".join(parts)

    def _parse_review_feedback(self, output: str) -> List[str]:
        """Parse structured feedback from Gemini's review."""
        suggestions = []

        # Look for numbered or bulleted lists
        lines = output.split("\n")
        for line in lines:
            line = line.strip()

            # Match numbered items: 1. , 2. , etc.
            if re.match(r"^\d+\.", line):
                suggestions.append(line)

            # Match bulleted items: - , * , etc.
            elif re.match(r"^[-*•]", line):
                suggestions.append(line[1:].strip())

            # Match severity markers
            elif any(
                severity in line.lower() for severity in ["critical:", "high:", "medium:", "low:"]
            ):
                suggestions.append(line)

        return suggestions

    def _extract_mentioned_files(self, output: str, context: Dict[str, Any]) -> List[str]:
        """Extract files mentioned in the review."""
        from typing import Set

        files: Set[str] = set()

        # Look for file path patterns
        file_pattern = r"`([^`]+\.(py|js|ts|java|go|rs|cpp|h))`"
        matches = re.findall(file_pattern, output)
        files.update(match[0] for match in matches)

        # Add files from context
        if context.get("files"):
            files.update(context["files"])

        return list(files)

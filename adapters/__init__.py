"""
AI Agent Adapters

This package contains adapters for different AI coding assistant CLI tools.
"""

from .base import AgentCapability, AgentResponse, BaseAdapter
from .claude_adapter import ClaudeAdapter
from .codex_adapter import CodexAdapter
from .copilot_adapter import CopilotAdapter
from .gemini_adapter import GeminiAdapter

__all__ = [
    "BaseAdapter",
    "AgentResponse",
    "AgentCapability",
    "ClaudeAdapter",
    "CodexAdapter",
    "GeminiAdapter",
    "CopilotAdapter",
]

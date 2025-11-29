"""
Workflow management for AI agent orchestration.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from adapters import AgentResponse, BaseAdapter


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""

    agent_name: str
    task_type: str
    adapter: BaseAdapter
    config: Dict[str, Any]

    def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute this workflow step.

        Args:
            context: Execution context

        Returns:
            AgentResponse from the agent
        """
        # Build task description based on type
        task = self._build_task_description(context)

        # Add step-specific context
        step_context = context.copy()
        step_context.update({"role": self.task_type, "agent": self.agent_name})

        # Execute using the adapter
        return self.adapter.execute_task(task, step_context)

    def _build_task_description(self, context: Dict[str, Any]) -> str:
        """Build task description based on step type and context."""
        base_task = context.get("task", "")

        if self.task_type == "implement":
            return f"Implement the following: {base_task}"

        elif self.task_type == "review":
            return f"Review the implementation of: {base_task}"

        elif self.task_type == "refine":
            return f"Refine the implementation based on review feedback for: {base_task}"

        elif self.task_type == "test":
            return f"Write tests for: {base_task}"

        elif self.task_type == "document":
            return f"Document the implementation of: {base_task}"

        else:
            return base_task


class WorkflowEngine:
    """Engine for executing workflows."""

    def __init__(self):
        self.logger = logging.getLogger("workflow_engine")
        self.steps: List[WorkflowStep] = []
        self.current_step = 0

    def set_workflow(self, steps: List[WorkflowStep]):
        """Set the workflow steps."""
        self.steps = steps
        self.current_step = 0
        self.logger.info(f"Workflow configured with {len(steps)} steps")

    def execute(self, context: Dict[str, Any]) -> List[AgentResponse]:
        """
        Execute the entire workflow.

        Args:
            context: Execution context

        Returns:
            List of responses from each step
        """
        results = []

        for i, step in enumerate(self.steps):
            self.current_step = i
            self.logger.info(f"Executing step {i+1}/{len(self.steps)}: {step.agent_name}")

            try:
                response = step.execute(context)
                results.append(response)

                # Update context with response for next step
                context["previous_response"] = response
                context["previous_output"] = response.output

            except Exception as e:
                self.logger.error(f"Step {i+1} failed: {e}", exc_info=True)
                # Create error response
                error_response = AgentResponse(success=False, output="", error=str(e))
                results.append(error_response)

        return results

    def get_progress(self) -> Dict[str, Any]:
        """Get current workflow progress."""
        return {
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "progress_percent": (self.current_step / len(self.steps) * 100) if self.steps else 0,
        }

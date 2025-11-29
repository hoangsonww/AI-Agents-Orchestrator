"""
Core orchestration logic for coordinating AI agents.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from adapters import BaseAdapter, ClaudeAdapter, CodexAdapter, CopilotAdapter, GeminiAdapter

from .task_manager import TaskManager
from .workflow import WorkflowEngine, WorkflowStep


class Orchestrator:
    """Main orchestrator for coordinating AI agents."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger("orchestrator")
        self.config = self._load_config(config_path)
        self.adapters: Dict[str, BaseAdapter] = {}
        self.workflow_engine = WorkflowEngine()
        self.task_manager = TaskManager()
        self.workspace_dir: Optional[Path] = None
        self.session_dir: Optional[Path] = None
        self._initialize_adapters()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file."""
        if config_path is None:
            config_path_obj: Path = Path(__file__).parent.parent / "config" / "agents.yaml"
        else:
            config_path_obj = Path(config_path)

        if not config_path_obj.exists():
            self.logger.warning(f"Config file not found: {config_path_obj}, using defaults")
            return self._get_default_config()

        with open(config_path_obj) as f:
            return yaml.safe_load(f)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "agents": {
                "codex": {"enabled": True, "command": "codex", "role": "implementation"},
                "gemini": {"enabled": True, "command": "gemini-cli", "role": "review"},
                "claude": {"enabled": True, "command": "claude", "role": "refinement"},
                "copilot": {
                    "enabled": False,
                    "command": "github-copilot-cli",
                    "role": "suggestions",
                },
            },
            "workflows": {
                "default": [
                    {"agent": "codex", "task": "implement"},
                    {"agent": "gemini", "task": "review"},
                    {"agent": "claude", "task": "refine"},
                ]
            },
            "settings": {"max_iterations": 3, "output_dir": "./output", "log_level": "INFO"},
        }

    def _initialize_adapters(self):
        """Initialize all configured adapters."""
        adapter_classes = {
            "codex": CodexAdapter,
            "gemini": GeminiAdapter,
            "claude": ClaudeAdapter,
            "copilot": CopilotAdapter,
        }

        agents_config = self.config.get("agents", {})

        for agent_name, agent_config in agents_config.items():
            if not agent_config.get("enabled", True):
                self.logger.info(f"Agent {agent_name} is disabled")
                continue

            adapter_class = adapter_classes.get(agent_name)
            if adapter_class is None:
                self.logger.warning(f"Unknown agent type: {agent_name}")
                continue

            # Add name to config
            agent_config["name"] = agent_name

            try:
                adapter = adapter_class(agent_config)  # type: ignore[abstract]

                # Check if available
                if not adapter.is_available():
                    self.logger.warning(
                        f"Agent {agent_name} is not available. "
                        f"Command '{adapter.command}' not found."
                    )
                    continue

                self.adapters[agent_name] = adapter
                self.logger.info(f"Initialized adapter: {agent_name}")

            except Exception as e:
                self.logger.error(f"Failed to initialize {agent_name}: {e}")

    def execute_task(
        self, task: str, workflow_name: str = "default", max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using the specified workflow.

        Args:
            task: The task description
            workflow_name: Name of the workflow to use
            max_iterations: Maximum iterations (overrides config)

        Returns:
            Dictionary with execution results
        """
        self.logger.info(f"Executing task: {task}")
        self.logger.info(f"Workflow: {workflow_name}")

        # Get workflow
        workflows = self.config.get("workflows", {})
        workflow_config = workflows.get(workflow_name)

        if not workflow_config:
            raise ValueError(f"Workflow '{workflow_name}' not found")

        # Build workflow steps
        steps = self._build_workflow_steps(workflow_config)
        self.workflow_engine.set_workflow(steps)

        # Get max iterations
        if max_iterations is None:
            max_iterations = self.config.get("settings", {}).get("max_iterations", 3)

        # Execute workflow
        context = {
            "task": task,
            "iteration": 0,
            "max_iterations": max_iterations,
            "working_dir": self.config.get("settings", {}).get("output_dir", "./output"),
        }

        results = {
            "task": task,
            "workflow": workflow_name,
            "iterations": [],
            "final_output": None,
            "success": False,
        }

        for iteration in range(max_iterations):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            self.logger.info(f"{'='*60}")

            context["iteration"] = iteration

            iteration_results = self._execute_workflow_iteration(steps, context)
            results["iterations"].append(iteration_results)  # type: ignore[attr-defined]

            # Check if we should continue
            if self._should_stop_iteration(iteration_results, context):
                self.logger.info("Stopping iterations: task appears complete")
                results["success"] = True
                break

            # Update context with results
            context = self._update_context(context, iteration_results)

        # Set final output
        if results["iterations"]:  # type: ignore[index]
            last_iteration = results["iterations"][-1]  # type: ignore[index]
            results["final_output"] = last_iteration.get("final_output")

        return results

    def _build_workflow_steps(self, workflow_config: List[Dict]) -> List[WorkflowStep]:
        """Build workflow steps from configuration."""
        steps = []

        for step_config in workflow_config:
            agent_name = step_config.get("agent")
            task_type = step_config.get("task")

            if agent_name not in self.adapters:
                self.logger.warning(f"Agent {agent_name} not available, skipping step")
                continue

            step = WorkflowStep(
                agent_name=agent_name,
                task_type=task_type,
                adapter=self.adapters[agent_name],
                config=step_config,
            )
            steps.append(step)

        return steps

    def _execute_workflow_iteration(
        self, steps: List[WorkflowStep], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute one iteration of the workflow."""
        iteration_results: Dict[str, Any] = {"steps": [], "final_output": None}

        for i, step in enumerate(steps):
            self.logger.info(f"\nStep {i+1}: {step.agent_name} - {step.task_type}")

            try:
                # Execute the step
                response = step.execute(context)

                step_result = {
                    "agent": step.agent_name,
                    "task": step.task_type,
                    "success": response.success,
                    "output": response.output,
                    "error": response.error,
                    "files_modified": response.files_modified,
                    "suggestions": response.suggestions,
                }

                iteration_results["steps"].append(step_result)

                # Log the result
                if response.success:
                    self.logger.info(f"✓ {step.agent_name} completed successfully")
                    if response.suggestions:
                        self.logger.info(f"  Suggestions: {len(response.suggestions)}")
                else:
                    self.logger.error(f"✗ {step.agent_name} failed: {response.error}")

                # Update context for next step
                context["previous_output"] = response.output
                context["previous_agent"] = step.agent_name

                if step.task_type == "review":
                    context["feedback"] = response.output
                    context["suggestions"] = response.suggestions
                elif step.task_type == "implement":
                    context["implementation"] = response.output
                    context["files"] = response.files_modified

                iteration_results["final_output"] = response.output

            except Exception as e:
                self.logger.error(f"Error executing step: {e}", exc_info=True)
                step_result = {
                    "agent": step.agent_name,
                    "task": step.task_type,
                    "success": False,
                    "error": str(e),
                }
                iteration_results["steps"].append(step_result)

        return iteration_results

    def _should_stop_iteration(
        self, iteration_results: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Determine if we should stop iterating."""
        # Stop if all steps succeeded and no significant feedback
        all_success = all(step.get("success", False) for step in iteration_results.get("steps", []))

        # Check if review step had minimal feedback
        has_minimal_feedback = True
        for step in iteration_results.get("steps", []):
            if step.get("task") == "review":
                suggestions = step.get("suggestions", [])
                # If review has many suggestions, continue iterating
                if len(suggestions) > 3:
                    has_minimal_feedback = False

        return all_success and has_minimal_feedback

    def _update_context(
        self, context: Dict[str, Any], iteration_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update context with iteration results."""
        # Preserve iteration count
        context["iteration"] += 1

        # Keep track of all iterations
        if "all_iterations" not in context:
            context["all_iterations"] = []
        context["all_iterations"].append(iteration_results)

        return context

    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self.adapters.keys())

    def get_workflows(self) -> List[str]:
        """Get list of available workflow names."""
        return list(self.config.get("workflows", {}).keys())

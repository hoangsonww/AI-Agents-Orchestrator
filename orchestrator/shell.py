"""
Interactive shell for AI Orchestrator.

Provides a REPL-style interface for multi-round conversations with AI agents,
similar to Claude Code and Codex CLIs.
"""

import json
import os
import readline
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from orchestrator import Orchestrator


class ConversationHistory:
    """Manages conversation history and context."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.current_agent: Optional[str] = None
        self.workflow: str = "default"
        self.context: Dict[str, Any] = {}

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)

    def get_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return {
            "history": self.messages[-10:],  # Last 10 messages for context
            "current_agent": self.current_agent,
            "workflow": self.workflow,
            "context": self.context,
        }

    def clear(self):
        """Clear conversation history."""
        self.messages.clear()
        self.context.clear()

    def save(self, filepath: str):
        """Save conversation history to file."""
        data = {
            "messages": self.messages,
            "current_agent": self.current_agent,
            "workflow": self.workflow,
            "context": self.context,
            "saved_at": datetime.now().isoformat(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: str):
        """Load conversation history from file."""
        with open(filepath) as f:
            data = json.load(f)
        self.messages = data.get("messages", [])
        self.current_agent = data.get("current_agent")
        self.workflow = data.get("workflow", "default")
        self.context = data.get("context", {})


class InteractiveShell:
    """Interactive shell for AI Orchestrator."""

    def __init__(self, config_path: Optional[str] = None):
        self.console = Console()
        self.orchestrator = Orchestrator(config_path)
        self.history = ConversationHistory()
        self.running = True

        # Initialize session directory with robust error handling
        self.session_dir = self._init_session_dir()

        # Setup readline for better UX
        self._setup_readline()

        # Shell commands
        self.commands = {
            "/help": self.cmd_help,
            "/exit": self.cmd_exit,
            "/quit": self.cmd_exit,
            "/clear": self.cmd_clear,
            "/history": self.cmd_history,
            "/agents": self.cmd_agents,
            "/workflows": self.cmd_workflows,
            "/switch": self.cmd_switch_agent,
            "/workflow": self.cmd_set_workflow,
            "/save": self.cmd_save_session,
            "/load": self.cmd_load_session,
            "/context": self.cmd_show_context,
            "/reset": self.cmd_reset,
            "/info": self.cmd_info,
            "/followup": self.cmd_followup,
        }

    def _init_session_dir(self) -> Path:
        """Initialize session directory with robust error handling."""
        try:
            session_dir = Path.home() / ".ai-orchestrator" / "sessions"

            # Check if path exists and handle conflicts
            if session_dir.exists():
                if not session_dir.is_dir():
                    # Path exists but is a file, not a directory
                    # Backup the file and create directory
                    backup = session_dir.parent / f"{session_dir.name}.backup"
                    session_dir.rename(backup)
                    self.console.print(f"[yellow]Warning: Moved file to {backup}[/yellow]")
                    session_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Create directory
                session_dir.mkdir(parents=True, exist_ok=True)

            # Verify we can write to the directory
            test_file = session_dir / ".test"
            try:
                test_file.touch(exist_ok=True)
                test_file.unlink()
            except (OSError, PermissionError) as e:
                self.console.print(f"[red]Warning: Cannot write to {session_dir}: {e}[/red]")
                # Fallback to temp directory
                import tempfile

                session_dir = Path(tempfile.gettempdir()) / "ai-orchestrator-sessions"
                session_dir.mkdir(parents=True, exist_ok=True)
                self.console.print(f"[yellow]Using temporary directory: {session_dir}[/yellow]")

            return session_dir

        except Exception as e:
            self.console.print(f"[red]Error initializing session directory: {e}[/red]")
            # Ultimate fallback to current directory
            fallback = Path.cwd() / ".sessions"
            fallback.mkdir(exist_ok=True)
            return fallback

    def _setup_readline(self):
        """Setup readline for command history and completion with robust error handling."""
        try:
            # History file
            history_file = self.session_dir / "history.txt"

            # Ensure history file exists and is writable
            try:
                if history_file.exists() and not history_file.is_file():
                    # Exists but is not a file (maybe a directory)
                    backup = self.session_dir / "history.txt.invalid"
                    history_file.rename(backup)
                    self.console.print(
                        f"[yellow]Warning: Renamed invalid history to {backup}[/yellow]"
                    )

                # Create if doesn't exist
                history_file.touch(exist_ok=True)

                # Try to read existing history
                readline.read_history_file(str(history_file))
            except (FileNotFoundError, PermissionError, OSError) as e:
                # History file operations are non-critical, continue without history
                self.console.print(f"[dim]Note: History disabled ({e})[/dim]", style="dim")

            # Save history on exit (only if we can write)
            if os.access(history_file, os.W_OK):
                import atexit

                atexit.register(self._save_history_safe, str(history_file))

            # Tab completion
            try:
                readline.parse_and_bind("tab: complete")
                readline.set_completer(self._completer)
            except Exception:
                pass  # Completion is optional

            # Vi or Emacs mode
            try:
                readline.parse_and_bind("set editing-mode emacs")
            except Exception:
                pass  # Editing mode is optional

        except Exception as e:
            # Readline setup is non-critical, continue without it
            self.console.print(
                f"[dim]Note: Advanced input features disabled ({e})[/dim]", style="dim"
            )

    def _save_history_safe(self, filename: str):
        """Safely save history file, catching any errors."""
        try:
            readline.write_history_file(filename)
        except Exception:
            pass  # Ignore history save errors

    def _completer(self, text: str, state: int):
        """Auto-completion for commands."""
        options = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]

        # Also complete agent names
        if text.startswith("/switch "):
            agent_prefix = text.split()[-1] if len(text.split()) > 1 else ""
            agents = self.orchestrator.get_available_agents()
            options.extend(
                [f"/switch {agent}" for agent in agents if agent.startswith(agent_prefix)]
            )

        if state < len(options):
            return options[state]
        return None

    def start(self):
        """Start the interactive shell."""
        self._show_welcome()

        while self.running:
            try:
                # Get user input
                prompt_text = self._get_prompt()
                user_input = Prompt.ask(prompt_text).strip()

                if not user_input:
                    continue

                # Check if it's a command
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                else:
                    # Regular message - check if this should be a follow-up
                    is_followup = self._should_follow_up(user_input)
                    if is_followup is not None:  # None means cancelled
                        self._handle_message(user_input, is_followup=is_followup)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit or /quit to exit[/yellow]")
                continue
            except EOFError:
                self.console.print("\n[yellow]Exiting...[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                if os.getenv("DEBUG"):
                    self.console.print_exception()

        self._show_goodbye()

    def _get_prompt(self) -> str:
        """Get the prompt string."""
        agent = self.history.current_agent or "orchestrator"
        workflow = self.history.workflow
        return f"[bold cyan]{agent}[/bold cyan] ([dim]{workflow}[/dim])"

    def _show_welcome(self):
        """Show welcome message."""
        welcome = """
# AI Orchestrator Interactive Shell

Welcome to the AI Orchestrator interactive shell!

This shell allows you to have multi-round conversations with AI coding assistants,
collaborate on tasks, and iterate on implementations.

**Available Commands:**
- `/help` - Show all commands
- `/followup <msg>` - Continue working on the previous task
- `/agents` - List available agents
- `/workflows` - List available workflows
- `/switch <agent>` - Switch to a specific agent
- `/exit` or `/quit` - Exit the shell

**Getting Started:**
Just type your request and press Enter. The system will coordinate the appropriate
AI agents to help you accomplish your task. After completion, use `/followup` to
continue iterating on the same task with additional requirements.

Type `/help` for more information.
        """
        self.console.print(Panel(Markdown(welcome), border_style="cyan", title="Welcome"))

        # Show available agents
        agents = self.orchestrator.get_available_agents()
        if agents:
            self.console.print(f"\n[green]Available agents:[/green] {', '.join(agents)}")
        else:
            self.console.print("\n[yellow]⚠ No agents currently available[/yellow]")

        self.console.print()

    def _show_goodbye(self):
        """Show goodbye message."""
        self.console.print("\n[cyan]Thank you for using AI Orchestrator![/cyan]")
        if self.history.messages:
            save = Confirm.ask("Would you like to save this session?", default=False)
            if save:
                filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = self.session_dir / filename
                self.history.save(str(filepath))
                self.console.print(f"[green]Session saved to:[/green] {filepath}")

    def _handle_command(self, command_str: str):
        """Handle shell commands."""
        parts = command_str.split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if command in self.commands:
            self.commands[command](args)
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[yellow]Type /help for available commands[/yellow]")

    def _should_follow_up(self, message: str) -> bool:
        """Determine if message should be treated as a follow-up."""
        # If we have a previous task, ask user
        if self.history.context.get("last_task"):
            # Check for obvious follow-up indicators
            followup_indicators = [
                "add",
                "also",
                "now",
                "then",
                "next",
                "additionally",
                "improve",
                "fix",
                "change",
                "update",
                "modify",
                "make it",
                "can you",
                "please",
                "try",
            ]

            message_lower = message.lower()
            has_indicator = any(word in message_lower for word in followup_indicators)

            # Auto follow-up if message is short and has indicators
            if len(message.split()) < 10 and has_indicator:
                self.console.print("[dim]💡 Detected as follow-up to previous task[/dim]")
                return True

            # Otherwise ask user
            self.console.print(f"\n[yellow]Continue previous task?[/yellow]")
            self.console.print(f"[dim]Previous: {self.history.context['last_task'][:60]}...[/dim]")

            response = Prompt.ask(
                "[cyan]Continue (c), New task (n), or Cancel (x)?[/cyan]",
                choices=["c", "n", "x"],
                default="c",
            )

            if response == "c":
                self.console.print("[dim]✓ Continuing previous task with context[/dim]\n")
                return True
            elif response == "x":
                self.console.print("[yellow]Cancelled[/yellow]")
                return None  # Signal to skip
            else:
                self.console.print("[dim]✓ Starting new task[/dim]\n")
                return False

        return False

    def _handle_message(self, message: str, is_followup: bool = False):
        """Handle user message and execute with orchestrator."""
        # Add to history
        self.history.add_message("user", message, {"is_followup": is_followup})

        # Get context from history - include previous results for follow-ups
        _ = self.history.get_context()  # noqa: F841

        # For follow-ups, add previous task context
        if is_followup and self.history.context.get("last_task"):
            previous_task = self.history.context["last_task"]
            previous_output = self.history.context.get("last_output", "")
            message = f"Previous task: {previous_task}\nPrevious result: {previous_output}\n\nFollow-up: {message}"

        # Show thinking indicator
        with self.console.status("[bold cyan]Orchestrating agents...[/bold cyan]"):
            try:
                # Execute with orchestrator
                results = self.orchestrator.execute_task(
                    task=message, workflow_name=self.history.workflow, max_iterations=3
                )

                # Display results
                self._display_results(results)

                # Add to history
                final_output = results.get("final_output", "")
                self.history.add_message(
                    "assistant",
                    final_output,
                    {
                        "workflow": results.get("workflow"),
                        "iterations": len(results.get("iterations", [])),
                    },
                )

                # Update context with results for future follow-ups
                self.history.context["last_task"] = message
                self.history.context["last_output"] = final_output
                self.history.context["last_success"] = results.get("success", False)

                # Store files from all iterations
                all_files = []
                if results.get("iterations"):
                    for iteration in results["iterations"]:
                        for step in iteration.get("steps", []):
                            if step.get("files_modified"):
                                all_files.extend(step["files_modified"])

                if all_files:
                    self.history.context["files"] = all_files
                    self.history.context["workspace"] = "./workspace"

            except Exception as e:
                self.console.print(f"[red]Error executing task: {e}[/red]")
                if os.getenv("DEBUG"):
                    self.console.print_exception()

    def _display_results(self, results: Dict[str, Any]):
        """Display execution results with enhanced formatting."""
        self.console.print()

        # Show iteration summary
        iterations = results.get("iterations", [])
        for i, iteration in enumerate(iterations, 1):
            self.console.print(f"[bold]Iteration {i}:[/bold]")

            for step in iteration.get("steps", []):
                agent = step.get("agent")
                task = step.get("task")
                success = step.get("success", False)

                status = "✓" if success else "✗"
                color = "green" if success else "red"

                self.console.print(f"  [{color}]{status}[/{color}] {agent} - {task}")

                # Show suggestions count if available
                suggestions = step.get("suggestions", [])
                if suggestions:
                    self.console.print(f"     [dim]Suggestions: {len(suggestions)}[/dim]")

            self.console.print()

        # Collect all generated files
        all_files = []
        for iteration in iterations:
            for step in iteration.get("steps", []):
                if step.get("files_modified"):
                    all_files.extend(step["files_modified"])

        # Show generated files
        if all_files:
            self.console.print("[bold cyan]📁 Generated Files:[/bold cyan]")
            for file in all_files:
                self.console.print(f"  📄 [green]{file}[/green]")
            self.console.print(f"\n[dim]Workspace: ./workspace[/dim]\n")

        # Show final output
        final_output = results.get("final_output", "")
        if final_output:
            # Full output - no truncation, but offer paging for very long output
            if len(final_output) > 2000:
                show_full = Confirm.ask(
                    f"Output is {len(final_output)} characters. Show full output?", default=False
                )
                if not show_full:
                    final_output = (
                        final_output[:2000] + "\n\n[dim]... (use /context to see full output)[/dim]"
                    )

            self.console.print(
                Panel(
                    final_output, title="[bold cyan]Final Output[/bold cyan]", border_style="cyan"
                )
            )

        # Show success status
        if results.get("success"):
            self.console.print("[bold green]✓ Task completed successfully![/bold green]")
            self.console.print(
                "[dim]Type your next task, or use /followup to continue this task[/dim]\n"
            )
        else:
            self.console.print("[bold yellow]⚠ Task completed with issues[/bold yellow]\n")

    # Command implementations

    def cmd_help(self, args: str):
        """Show help information."""
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")

        table.add_row("/help", "Show this help message")
        table.add_row("/exit, /quit", "Exit the interactive shell")
        table.add_row("/clear", "Clear the screen")
        table.add_row(
            "/followup <msg>", "Continue working on the previous task with new instructions"
        )
        table.add_row("/history", "Show conversation history")
        table.add_row("/agents", "List available agents")
        table.add_row("/workflows", "List available workflows")
        table.add_row("/switch <agent>", "Switch to a specific agent for direct communication")
        table.add_row("/workflow <name>", "Change the workflow")
        table.add_row("/save [filename]", "Save current session")
        table.add_row("/load <filename>", "Load a previous session")
        table.add_row("/context", "Show current context")
        table.add_row("/reset", "Reset conversation and context")
        table.add_row("/info", "Show system information")

        self.console.print(table)

    def cmd_exit(self, args: str):
        """Exit the shell."""
        self.running = False

    def cmd_clear(self, args: str):
        """Clear the screen."""
        os.system("clear" if os.name != "nt" else "cls")

    def cmd_history(self, args: str):
        """Show conversation history."""
        if not self.history.messages:
            self.console.print("[yellow]No conversation history[/yellow]")
            return

        self.console.print("\n[bold]Conversation History:[/bold]\n")

        for i, msg in enumerate(self.history.messages, 1):
            role = msg["role"]
            content = msg["content"]
            timestamp = msg.get("timestamp", "unknown")

            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."

            color = "cyan" if role == "user" else "green"
            self.console.print(f"{i}. [{color}]{role}[/{color}] ({timestamp})")
            self.console.print(f"   {content}\n")

    def cmd_agents(self, args: str):
        """List available agents."""
        agents = self.orchestrator.get_available_agents()

        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            return

        table = Table(title="Available Agents")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")

        for agent in agents:
            table.add_row(agent, "✓ Available")

        self.console.print(table)

    def cmd_workflows(self, args: str):
        """List available workflows."""
        workflows = self.orchestrator.get_workflows()

        table = Table(title="Available Workflows")
        table.add_column("Workflow", style="cyan")
        table.add_column("Current", style="green")

        for workflow in workflows:
            current = "✓" if workflow == self.history.workflow else ""
            table.add_row(workflow, current)

        self.console.print(table)

    def cmd_switch_agent(self, args: str):
        """Switch to a specific agent."""
        if not args:
            self.console.print("[yellow]Usage: /switch <agent_name>[/yellow]")
            self.cmd_agents("")
            return

        agent = args.strip()
        agents = self.orchestrator.get_available_agents()

        if agent not in agents:
            self.console.print(f"[red]Agent '{agent}' not available[/red]")
            self.cmd_agents("")
            return

        self.history.current_agent = agent
        self.console.print(f"[green]Switched to agent: {agent}[/green]")

    def cmd_set_workflow(self, args: str):
        """Change the workflow."""
        if not args:
            self.console.print("[yellow]Usage: /workflow <workflow_name>[/yellow]")
            self.cmd_workflows("")
            return

        workflow = args.strip()
        workflows = self.orchestrator.get_workflows()

        if workflow not in workflows:
            self.console.print(f"[red]Workflow '{workflow}' not found[/red]")
            self.cmd_workflows("")
            return

        self.history.workflow = workflow
        self.console.print(f"[green]Switched to workflow: {workflow}[/green]")

    def cmd_save_session(self, args: str):
        """Save current session."""
        if args:
            filename = args.strip()
        else:
            filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.session_dir / filename
        self.history.save(str(filepath))
        self.console.print(f"[green]Session saved to:[/green] {filepath}")

    def cmd_load_session(self, args: str):
        """Load a previous session."""
        if not args:
            # List available sessions
            sessions = list(self.session_dir.glob("*.json"))
            if not sessions:
                self.console.print("[yellow]No saved sessions found[/yellow]")
                return

            self.console.print("[bold]Available sessions:[/bold]")
            for i, session in enumerate(sessions, 1):
                self.console.print(f"{i}. {session.name}")

            self.console.print("\n[yellow]Usage: /load <filename>[/yellow]")
            return

        filename = args.strip()
        filepath = self.session_dir / filename

        if not filepath.exists():
            self.console.print(f"[red]Session file not found: {filename}[/red]")
            return

        self.history.load(str(filepath))
        self.console.print(f"[green]Session loaded from:[/green] {filepath}")
        self.console.print(f"[green]Loaded {len(self.history.messages)} messages[/green]")

    def cmd_show_context(self, args: str):
        """Show current context."""
        context = self.history.get_context()

        self.console.print("\n[bold]Current Context:[/bold]")
        self.console.print(f"Agent: {context['current_agent'] or 'orchestrator'}")
        self.console.print(f"Workflow: {context['workflow']}")
        self.console.print(f"Messages in history: {len(self.history.messages)}")

        if context["context"]:
            self.console.print("\n[bold]Context Data:[/bold]")
            for key, value in context["context"].items():
                if isinstance(value, list):
                    self.console.print(f"  {key}: {len(value)} items")
                else:
                    self.console.print(f"  {key}: {value}")

    def cmd_reset(self, args: str):
        """Reset conversation and context."""
        confirm = Confirm.ask("Are you sure you want to reset the conversation?", default=False)
        if confirm:
            self.history.clear()
            self.history.current_agent = None
            self.history.workflow = "default"
            self.console.print("[green]Conversation and context reset[/green]")
        else:
            self.console.print("[yellow]Reset cancelled[/yellow]")

    def cmd_info(self, args: str):
        """Show system information."""
        agents = self.orchestrator.get_available_agents()
        workflows = self.orchestrator.get_workflows()

        info = f"""
[bold cyan]AI Orchestrator Information[/bold cyan]

[bold]Available Agents:[/bold] {len(agents)}
{', '.join(agents) if agents else 'None'}

[bold]Available Workflows:[/bold] {len(workflows)}
{', '.join(workflows)}

[bold]Current Session:[/bold]
- Agent: {self.history.current_agent or 'orchestrator'}
- Workflow: {self.history.workflow}
- Messages: {len(self.history.messages)}

[bold]Session Directory:[/bold]
{self.session_dir}
        """

        self.console.print(Panel(info.strip(), border_style="cyan"))

    def cmd_followup(self, args: str):
        """Continue working on the previous task."""
        if not self.history.context.get("last_task"):
            self.console.print(
                "[yellow]No previous task to follow up on. Start a new task first.[/yellow]"
            )
            return

        if not args:
            self.console.print("[yellow]Please provide instructions for the follow-up.[/yellow]")
            self.console.print("[dim]Example: /followup add error handling[/dim]")
            return

        # Show context
        last_task = self.history.context.get("last_task", "")
        files = self.history.context.get("files", [])

        self.console.print(f"\n[bold cyan]Following up on:[/bold cyan] {last_task[:100]}...")
        if files:
            self.console.print(
                f"[dim]Files in context: {', '.join(files[:3])}{'...' if len(files) > 3 else ''}[/dim]\n"
            )

        # Handle as a follow-up message
        self._handle_message(args, is_followup=True)

"""
Interactive shell for AI Orchestrator.

Provides a REPL-style interface for multi-round conversations with AI agents,
similar to Claude Code and Codex CLIs.
"""

import os
import sys
import readline
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax

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
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.messages.append(message)

    def get_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return {
            'history': self.messages[-10:],  # Last 10 messages for context
            'current_agent': self.current_agent,
            'workflow': self.workflow,
            'context': self.context
        }

    def clear(self):
        """Clear conversation history."""
        self.messages.clear()
        self.context.clear()

    def save(self, filepath: str):
        """Save conversation history to file."""
        data = {
            'messages': self.messages,
            'current_agent': self.current_agent,
            'workflow': self.workflow,
            'context': self.context,
            'saved_at': datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: str):
        """Load conversation history from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.messages = data.get('messages', [])
        self.current_agent = data.get('current_agent')
        self.workflow = data.get('workflow', 'default')
        self.context = data.get('context', {})


class InteractiveShell:
    """Interactive shell for AI Orchestrator."""

    def __init__(self, config_path: Optional[str] = None):
        self.console = Console()
        self.orchestrator = Orchestrator(config_path)
        self.history = ConversationHistory()
        self.running = True
        self.session_dir = Path.home() / '.ai-orchestrator' / 'sessions'
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Setup readline for better UX
        self._setup_readline()

        # Shell commands
        self.commands = {
            '/help': self.cmd_help,
            '/exit': self.cmd_exit,
            '/quit': self.cmd_exit,
            '/clear': self.cmd_clear,
            '/history': self.cmd_history,
            '/agents': self.cmd_agents,
            '/workflows': self.cmd_workflows,
            '/switch': self.cmd_switch_agent,
            '/workflow': self.cmd_set_workflow,
            '/save': self.cmd_save_session,
            '/load': self.cmd_load_session,
            '/context': self.cmd_show_context,
            '/reset': self.cmd_reset,
            '/info': self.cmd_info,
        }

    def _setup_readline(self):
        """Setup readline for command history and completion."""
        # History file
        history_file = self.session_dir / 'history.txt'
        try:
            readline.read_history_file(str(history_file))
        except FileNotFoundError:
            pass

        # Save history on exit
        import atexit
        atexit.register(readline.write_history_file, str(history_file))

        # Tab completion
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self._completer)

        # Vi or Emacs mode
        readline.parse_and_bind('set editing-mode emacs')

    def _completer(self, text: str, state: int):
        """Auto-completion for commands."""
        options = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]

        # Also complete agent names
        if text.startswith('/switch '):
            agent_prefix = text.split()[-1] if len(text.split()) > 1 else ''
            agents = self.orchestrator.get_available_agents()
            options.extend([f'/switch {agent}' for agent in agents if agent.startswith(agent_prefix)])

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
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                else:
                    # Regular message - execute with orchestrator
                    self._handle_message(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit or /quit to exit[/yellow]")
                continue
            except EOFError:
                self.console.print("\n[yellow]Exiting...[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                if os.getenv('DEBUG'):
                    self.console.print_exception()

        self._show_goodbye()

    def _get_prompt(self) -> str:
        """Get the prompt string."""
        agent = self.history.current_agent or 'orchestrator'
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
- `/agents` - List available agents
- `/workflows` - List available workflows
- `/switch <agent>` - Switch to a specific agent
- `/exit` or `/quit` - Exit the shell

**Getting Started:**
Just type your request and press Enter. The system will coordinate the appropriate
AI agents to help you accomplish your task.

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
        args = parts[1] if len(parts) > 1 else ''

        if command in self.commands:
            self.commands[command](args)
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[yellow]Type /help for available commands[/yellow]")

    def _handle_message(self, message: str):
        """Handle user message and execute with orchestrator."""
        # Add to history
        self.history.add_message('user', message)

        # Get context from history
        context = self.history.get_context()

        # Show thinking indicator
        with self.console.status("[bold cyan]Orchestrating agents...[/bold cyan]"):
            try:
                # Execute with orchestrator
                results = self.orchestrator.execute_task(
                    task=message,
                    workflow_name=self.history.workflow,
                    max_iterations=3
                )

                # Display results
                self._display_results(results)

                # Add to history
                final_output = results.get('final_output', '')
                self.history.add_message('assistant', final_output, {
                    'workflow': results.get('workflow'),
                    'iterations': len(results.get('iterations', []))
                })

                # Update context with results
                if results.get('iterations'):
                    last_iteration = results['iterations'][-1]
                    for step in last_iteration.get('steps', []):
                        if step.get('files_modified'):
                            self.history.context['files'] = step['files_modified']

            except Exception as e:
                self.console.print(f"[red]Error executing task: {e}[/red]")
                if os.getenv('DEBUG'):
                    self.console.print_exception()

    def _display_results(self, results: Dict[str, Any]):
        """Display execution results."""
        self.console.print()

        # Show iteration summary
        iterations = results.get('iterations', [])
        for i, iteration in enumerate(iterations, 1):
            self.console.print(f"[bold]Iteration {i}:[/bold]")

            for step in iteration.get('steps', []):
                agent = step.get('agent')
                task = step.get('task')
                success = step.get('success', False)

                status = "✓" if success else "✗"
                color = "green" if success else "red"

                self.console.print(f"  [{color}]{status}[/{color}] {agent} - {task}")

                # Show suggestions count if available
                suggestions = step.get('suggestions', [])
                if suggestions:
                    self.console.print(f"     [dim]Suggestions: {len(suggestions)}[/dim]")

            self.console.print()

        # Show final output
        final_output = results.get('final_output', '')
        if final_output:
            # Limit output length in interactive mode
            if len(final_output) > 1000:
                final_output = final_output[:1000] + "\n\n[dim]... (output truncated)[/dim]"

            self.console.print(Panel(
                final_output,
                title="[bold cyan]Final Output[/bold cyan]",
                border_style="cyan"
            ))

        # Show success status
        if results.get('success'):
            self.console.print("[bold green]✓ Task completed successfully![/bold green]\n")
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
        os.system('clear' if os.name != 'nt' else 'cls')

    def cmd_history(self, args: str):
        """Show conversation history."""
        if not self.history.messages:
            self.console.print("[yellow]No conversation history[/yellow]")
            return

        self.console.print("\n[bold]Conversation History:[/bold]\n")

        for i, msg in enumerate(self.history.messages, 1):
            role = msg['role']
            content = msg['content']
            timestamp = msg.get('timestamp', 'unknown')

            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."

            color = "cyan" if role == 'user' else "green"
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
            self.cmd_agents('')
            return

        agent = args.strip()
        agents = self.orchestrator.get_available_agents()

        if agent not in agents:
            self.console.print(f"[red]Agent '{agent}' not available[/red]")
            self.cmd_agents('')
            return

        self.history.current_agent = agent
        self.console.print(f"[green]Switched to agent: {agent}[/green]")

    def cmd_set_workflow(self, args: str):
        """Change the workflow."""
        if not args:
            self.console.print("[yellow]Usage: /workflow <workflow_name>[/yellow]")
            self.cmd_workflows('')
            return

        workflow = args.strip()
        workflows = self.orchestrator.get_workflows()

        if workflow not in workflows:
            self.console.print(f"[red]Workflow '{workflow}' not found[/red]")
            self.cmd_workflows('')
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
            sessions = list(self.session_dir.glob('*.json'))
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

        if context['context']:
            self.console.print("\n[bold]Context Data:[/bold]")
            for key, value in context['context'].items():
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

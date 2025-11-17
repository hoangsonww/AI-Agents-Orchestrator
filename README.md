# AI Coding Tools Collaborative

A powerful orchestration system that enables multiple AI coding assistants (Claude Code, Codex, Copilot CLI, Gemini CLI) to collaborate on software development tasks.

## Overview

This project provides a wrapper CLI that coordinates multiple AI agents to work together on coding tasks:

1. **Implementation**: Codex implements the initial solution
2. **Review**: Gemini reviews code for SOLID principles, best practices, and design patterns
3. **Refinement**: Claude implements feedback and improvements
4. **Iteration**: The process continues as needed until the task is complete

## Features

- 🤝 **Multi-Agent Collaboration**: Coordinate multiple AI coding assistants
- 💬 **Interactive Shell**: REPL-style interface with multi-round conversations (like Claude Code & Codex CLIs)
- 📝 **Conversation History**: Context preservation across interactions
- 💾 **Session Management**: Save and load conversation sessions
- 🔧 **Extensible Architecture**: Easy to add new AI agents
- ⚙️ **Configurable Workflows**: Define custom collaboration patterns
- 📊 **Detailed Logging**: Track agent interactions and decisions
- 🧪 **Comprehensive Testing**: Ensure reliable agent communication
- 🎯 **Smart Orchestration**: Intelligent task routing and feedback loops

## Architecture

```
┌─────────────────────────────────────────────┐
│         AI Orchestrator CLI                 │
│  (User Interface & Workflow Management)     │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │   Orchestrator    │
        │   Core Engine     │
        └─────────┬─────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    │             │             │             │
┌───▼───┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│ Codex │   │ Gemini  │   │ Claude  │   │ Copilot │
│Adapter│   │ Adapter │   │ Adapter │   │ Adapter │
└───┬───┘   └────┬────┘   └────┬────┘   └────┬────┘
    │            │             │             │
┌───▼───┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│Codex  │   │Gemini   │   │Claude   │   │Copilot  │
│CLI    │   │CLI      │   │Code     │   │CLI      │
└───────┘   └─────────┘   └─────────┘   └─────────┘
```

## Installation

### Prerequisites

- Python 3.8+
- AI CLI tools installed and authenticated:
  - Claude Code
  - OpenAI Codex CLI
  - GitHub Copilot CLI
  - Google Gemini CLI

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd AI-Coding-Tools-Collaborative

# Install dependencies
pip install -r requirements.txt

# Make the CLI executable
chmod +x ai-orchestrator

# Optional: Add to PATH
ln -s $(pwd)/ai-orchestrator /usr/local/bin/ai-orchestrator
```

## Configuration

Create or modify `config/agents.yaml` to configure your AI agents:

```yaml
agents:
  codex:
    enabled: true
    command: "codex"
    role: "implementation"

  gemini:
    enabled: true
    command: "gemini-cli"
    role: "review"

  claude:
    enabled: true
    command: "claude"
    role: "refinement"

  copilot:
    enabled: false
    command: "github-copilot-cli"
    role: "suggestions"

workflows:
  default:
    - agent: "codex"
      task: "implement"
    - agent: "gemini"
      task: "review"
    - agent: "claude"
      task: "refine"
```

## Usage

### Interactive Shell (Recommended)

Start an interactive shell for multi-round conversations, similar to Claude Code and Codex CLIs:

```bash
# Start interactive shell
./ai-orchestrator shell

# Start with specific workflow
./ai-orchestrator shell --workflow thorough
```

**Interactive features:**
- Multi-round conversations with context preservation
- Switch between agents on-the-fly
- Save and load conversation sessions
- Full readline support (arrow keys, command history, tab completion)
- Shell commands for control (/help, /switch, /save, etc.)

See [Interactive Shell Guide](docs/interactive-shell.md) for detailed documentation.

**Example interactive session:**

```
orchestrator (default) > Create a user authentication module with JWT

✓ Task completed successfully!

orchestrator (default) > Add password reset functionality

✓ Task completed successfully!

orchestrator (default) > /save auth-module
Session saved!

orchestrator (default) > /exit
```

### One-Shot Command Mode

For single, non-interactive tasks:

```bash
# Run with default workflow
./ai-orchestrator run "Create a REST API with user authentication"

# Specify a custom workflow
./ai-orchestrator run "Implement a binary search tree" --workflow thorough

# Dry run to see the execution plan
./ai-orchestrator run "Add error handling to the payment service" --dry-run

# Verbose mode for detailed logging
./ai-orchestrator run "Refactor the database layer" --verbose
```

### Advanced Usage

```bash
# Set maximum iterations
./ai-orchestrator run "Implement and test a caching layer" --max-iterations 5

# Output to specific directory
./ai-orchestrator run "Generate a CLI tool" --output ./output

# Custom configuration
./ai-orchestrator run "Task description" --config ./my-config.yaml
```

## Workflow Examples

### 1. Standard Implementation Flow

```bash
./ai-orchestrator run "Create a user authentication module with JWT tokens"
```

**Process:**
1. Codex implements the authentication module
2. Gemini reviews for SOLID principles, security best practices
3. Claude implements Gemini's feedback
4. Process repeats if needed

### 2. Review-Only Workflow

```bash
./ai-orchestrator run "Review this code" --workflow review-only
```

**Process:**
1. Gemini reviews existing code
2. Claude implements improvements

### 3. Interactive Development Session

```bash
./ai-orchestrator shell

> Create a task queue system
> Add priority support
> Add worker pool management
> Write tests for the task queue
> /save task-queue-project
```

**Process:**
Multi-round conversation with context preservation, allowing iterative refinement

## Project Structure

```
AI-Coding-Tools-Collaborative/
├── ai-orchestrator           # Main CLI entry point
├── orchestrator/
│   ├── __init__.py
│   ├── core.py              # Core orchestration logic
│   ├── workflow.py          # Workflow management
│   ├── task_manager.py      # Task distribution
│   └── shell.py             # Interactive shell/REPL
├── adapters/
│   ├── __init__.py
│   ├── base.py              # Base adapter interface
│   ├── cli_communicator.py  # Robust CLI communication
│   ├── claude_adapter.py    # Claude Code adapter
│   ├── codex_adapter.py     # Codex adapter
│   ├── gemini_adapter.py    # Gemini adapter
│   └── copilot_adapter.py   # Copilot adapter
├── config/
│   └── agents.yaml          # Agent and workflow configuration
├── tests/
│   ├── __init__.py
│   ├── test_adapters.py     # Adapter tests
│   ├── test_orchestrator.py # Orchestrator tests
│   ├── test_integration.py  # End-to-end tests
│   └── test_shell.py        # Interactive shell tests
├── docs/
│   ├── architecture.md      # Architecture details
│   ├── interactive-shell.md # Interactive shell guide
│   ├── adding-agents.md     # Guide for adding new agents
│   └── workflows.md         # Workflow configuration guide
├── examples/
│   └── sample_tasks.md      # Example tasks and outputs
├── requirements.txt
└── README.md
```

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/test_adapters.py -v

# Run with coverage
python -m pytest --cov=orchestrator --cov=adapters tests/

# Integration tests
python -m pytest tests/test_integration.py --integration
```

## How It Works

### 1. Task Reception
The orchestrator receives a task from the user via the CLI.

### 2. Workflow Selection
Based on configuration or flags, the appropriate workflow is selected.

### 3. Agent Execution
Agents are invoked in sequence according to the workflow:

- **Implementation Agent (Codex)**: Creates initial code
- **Review Agent (Gemini)**: Analyzes code for:
  - SOLID principles
  - Design patterns
  - Best practices
  - Performance issues
  - Security vulnerabilities
- **Refinement Agent (Claude)**: Implements feedback

### 4. Iteration
The process continues until:
- Quality thresholds are met
- Maximum iterations reached
- No more feedback is generated

### 5. Output
Final code and collaboration logs are provided to the user.

## Adding New Agents

See [docs/adding-agents.md](docs/adding-agents.md) for detailed instructions.

Basic steps:
1. Create adapter in `adapters/`
2. Implement `BaseAdapter` interface
3. Add configuration in `config/agents.yaml`
4. Add tests in `tests/`

## Contributing

Contributions are welcome! Please see our contributing guidelines.

## License

See LICENSE.md for details.

## Troubleshooting

### Agent Not Found
Ensure the CLI tool is installed and in your PATH:
```bash
which claude
which codex
which gemini-cli
which github-copilot-cli
```

### Authentication Errors
Make sure you're logged in to each service:
```bash
claude auth login
codex auth login
gemini-cli auth login
github-copilot-cli auth login
```

### Configuration Issues
Validate your configuration:
```bash
./ai-orchestrator --validate-config
```

## FAQ

**Q: Can I use only some of the agents?**
A: Yes! Configure which agents are enabled in `config/agents.yaml`.

**Q: How do I create custom workflows?**
A: Edit `config/workflows.yaml` to define your own collaboration patterns.

**Q: Is internet connection required?**
A: Yes, all AI agents require internet to function.

**Q: Can I run this in CI/CD?**
A: Yes! Use the `--non-interactive` flag for automation.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation in `docs/`
- Review example tasks in `examples/`

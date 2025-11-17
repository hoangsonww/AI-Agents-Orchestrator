# Interactive Shell Guide

The AI Orchestrator includes a powerful interactive shell that provides a REPL-style interface for multi-round conversations with AI agents, similar to Claude Code and Codex CLIs.

## Starting the Interactive Shell

```bash
# Start with default settings
./ai-orchestrator shell

# Start with a specific workflow
./ai-orchestrator shell --workflow thorough

# Alternative command
./ai-orchestrator interactive
```

## Features

### Multi-Round Conversations

Unlike the one-shot `run` command, the interactive shell maintains conversation history and context across multiple interactions:

```
orchestrator (default) > Create a user authentication module with JWT tokens
[Agent orchestration begins...]

orchestrator (default) > Now add password reset functionality
[Continues with previous context...]

orchestrator (default) > Write tests for the authentication module
[Builds on previous work...]
```

### Conversation History

The shell automatically maintains conversation history:
- Previous messages and responses
- File modifications
- Agent suggestions
- Context data

Access with `/history` command.

### Session Management

Save and load conversation sessions:

```
orchestrator (default) > /save my-auth-project
Session saved to: /home/user/.ai-orchestrator/sessions/my-auth-project.json

# Later...
orchestrator (default) > /load my-auth-project
Session loaded from: ...
Loaded 15 messages
```

### Agent Switching

Switch to communicate directly with a specific agent:

```
orchestrator (default) > /switch claude
Switched to agent: claude

claude (default) > Refactor this code to use dependency injection
[Claude works directly on the task...]

claude (default) > /switch codex
Switched to agent: codex

codex (default) > Implement the user service
[Codex implements...]
```

## Shell Commands

All commands start with `/` to distinguish them from regular prompts.

### Navigation & Information

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/info` | Show system and session information |
| `/agents` | List all available agents |
| `/workflows` | List all available workflows |
| `/context` | Show current conversation context |
| `/history` | Show conversation history |

### Session Control

| Command | Description |
|---------|-------------|
| `/switch <agent>` | Switch to a specific agent |
| `/workflow <name>` | Change the workflow |
| `/reset` | Reset conversation and context |
| `/clear` | Clear the screen |

### Session Persistence

| Command | Description |
|---------|-------------|
| `/save [filename]` | Save current session |
| `/load <filename>` | Load a previous session |

### Exit

| Command | Description |
|---------|-------------|
| `/exit` or `/quit` | Exit the interactive shell |

## Usage Patterns

### Pattern 1: Iterative Development

```
orchestrator (default) > Create a REST API for a blog

# Review output, then refine
orchestrator (default) > Add authentication to the API

# Continue building
orchestrator (default) > Add rate limiting middleware

# Test
orchestrator (default) > Write integration tests for the API
```

### Pattern 2: Code Review Workflow

```
# Switch to review workflow
orchestrator (default) > /workflow review-only

# Review existing code
orchestrator (default) > Review src/services/payment.py for SOLID principles

# See suggestions
[Gemini provides detailed review...]

# Implement improvements
orchestrator (default) > Implement the suggested improvements
```

### Pattern 3: Direct Agent Communication

```
# Switch to specific agent for specialized work
orchestrator (default) > /switch gemini
Switched to agent: gemini

# Ask for architecture advice
gemini (default) > What's the best architecture for a microservices-based e-commerce platform?

[Gemini provides detailed architectural guidance...]

# Switch to implementation agent
gemini (default) > /switch codex

# Implement based on architecture
codex (default) > Implement the order service using the architecture from Gemini
```

### Pattern 4: Multi-Session Project

```
# Day 1: Start project
orchestrator (default) > Create a task management application with user auth
...
orchestrator (default) > /save task-app-day1

# Day 2: Continue
orchestrator (default) > /load task-app-day1
orchestrator (default) > Add task assignment and notifications
...
orchestrator (default) > /save task-app-day2

# Day 3: Finalize
orchestrator (default) > /load task-app-day2
orchestrator (default) > Add tests and documentation
...
orchestrator (default) > /save task-app-final
```

## Advanced Features

### Context Preservation

The shell maintains rich context across interactions:

- **Conversation History**: Last 10 messages for context
- **File Tracking**: Files modified during the session
- **Agent State**: Current agent and workflow
- **Custom Context**: Additional data from previous iterations

View with `/context`:

```
orchestrator (default) > /context

Current Context:
Agent: orchestrator
Workflow: default
Messages in history: 5

Context Data:
  files: 3 items
  previous_agent: codex
```

### Readline Support

The shell includes full readline support:

- **Arrow Keys**: Navigate command history (↑/↓)
- **Tab Completion**: Complete commands and agent names
- **History**: Persistent command history across sessions
- **Emacs Keybindings**: Ctrl+A (start), Ctrl+E (end), etc.

### Auto-Save on Exit

When you exit the shell with messages in history, you'll be prompted to save:

```
orchestrator (default) > /exit

Would you like to save this session? (y/N): y
Session saved to: /home/user/.ai-orchestrator/sessions/session_20250117_143022.json

Thank you for using AI Orchestrator!
```

## Session Storage

Sessions are stored in `~/.ai-orchestrator/sessions/` as JSON files.

### Session Format

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Create a REST API",
      "timestamp": "2025-01-17T14:30:22.123456",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "I'll create a REST API...",
      "timestamp": "2025-01-17T14:30:45.789012",
      "metadata": {
        "workflow": "default",
        "iterations": 2
      }
    }
  ],
  "current_agent": "orchestrator",
  "workflow": "default",
  "context": {
    "files": ["api.py", "tests.py"]
  },
  "saved_at": "2025-01-17T14:35:00.000000"
}
```

## Tips & Best Practices

### 1. Use Descriptive Save Names

```bash
# Good
/save user-auth-module
/save api-refactoring-jan17

# Less useful
/save session1
/save temp
```

### 2. Review Context Periodically

```bash
# Check what's in context
/context

# Review history
/history

# See files being tracked
/context
```

### 3. Switch Workflows for Different Tasks

```bash
# Quick prototyping
/workflow quick

# Critical production code
/workflow thorough

# Code review
/workflow review-only
```

### 4. Use Agent Switching Strategically

```bash
# Get architecture advice from Gemini
/switch gemini
> Design a microservices architecture

# Implement with Codex
/switch codex
> Implement the order service

# Refine with Claude
/switch claude
> Refactor for better error handling
```

### 5. Save Regularly

Save your session after significant milestones:

```bash
# After major implementation
/save project-milestone1

# After review and fixes
/save project-milestone2

# Final version
/save project-final
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `↑` / `↓` | Navigate command history |
| `Tab` | Auto-complete commands |
| `Ctrl+C` | Interrupt (doesn't exit) |
| `Ctrl+D` | Exit shell (EOF) |
| `Ctrl+A` | Move to start of line |
| `Ctrl+E` | Move to end of line |
| `Ctrl+K` | Delete to end of line |
| `Ctrl+U` | Delete to start of line |
| `Ctrl+L` | Clear screen (or use `/clear`) |

## Troubleshooting

### Command Not Found

```
Unknown command: /foo
Type /help for available commands
```

**Solution**: Check `/help` for correct command spelling.

### Agent Not Available

```
Agent 'codex' not available
```

**Solution**: Run `/agents` to see which agents are available, then switch to one that is.

### Session File Not Found

```
Session file not found: my-session.json
```

**Solution**: Run `/load` without arguments to see available sessions.

### Can't Exit with Ctrl+C

```
Use /exit or /quit to exit
```

**Solution**: `Ctrl+C` interrupts the current operation but doesn't exit. Use `/exit` or `/quit` to leave the shell.

## Comparison: Shell vs Run Command

| Feature | Interactive Shell | Run Command |
|---------|------------------|-------------|
| **Multi-round** | ✅ Yes | ❌ No |
| **Context preservation** | ✅ Yes | ❌ No |
| **Session save/load** | ✅ Yes | ❌ No |
| **Agent switching** | ✅ Yes | ❌ No |
| **Command history** | ✅ Yes | ❌ No |
| **Best for** | Exploration, iteration | One-shot tasks |

## Examples

### Example 1: Building a Feature Iteratively

```bash
$ ./ai-orchestrator shell

orchestrator (default) > Create a user registration system with email validation

✓ Task completed successfully!

orchestrator (default) > Add password strength requirements

✓ Task completed successfully!

orchestrator (default) > Add unit tests for the validation logic

✓ Task completed successfully!

orchestrator (default) > /save user-registration-system
Session saved to: ~/.ai-orchestrator/sessions/user-registration-system.json

orchestrator (default) > /exit
```

### Example 2: Code Review Session

```bash
$ ./ai-orchestrator shell --workflow review-only

orchestrator (review-only) > Review src/payment_processor.py

[Gemini provides detailed review with SOLID principles analysis...]

orchestrator (review-only) > Implement the top 3 critical issues

[Claude implements improvements...]

orchestrator (review-only) > Re-review the changes

[Gemini re-reviews...]

orchestrator (review-only) > /save payment-review-jan17
```

### Example 3: Multi-Agent Collaboration

```bash
$ ./ai-orchestrator shell

orchestrator (default) > /switch gemini
Switched to agent: gemini

gemini (default) > What's the best approach for implementing a caching layer?

[Gemini provides architectural guidance...]

gemini (default) > /switch codex
Switched to agent: codex

codex (default) > Implement the caching layer using the guidance from Gemini

[Codex implements...]

codex (default) > /switch claude
Switched to agent: claude

claude (default) > Review and optimize the caching implementation

[Claude refines...]

claude (default) > /save caching-layer-complete
```

## Future Enhancements

Planned features for the interactive shell:

- **Streaming Responses**: See agent responses as they're generated
- **Syntax Highlighting**: Color-coded code output
- **File Browser**: Browse and edit files directly in shell
- **Multi-Agent Chat**: Have multiple agents discuss in real-time
- **Collaborative Mode**: Multiple users in same session
- **Voice Input**: Speak commands instead of typing
- **Export**: Export sessions to markdown or PDF

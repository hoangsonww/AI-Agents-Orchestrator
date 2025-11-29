# Sample Tasks and Usage Examples

## Basic Usage

### Example 1: Create a REST API

```bash
./ai-orchestrator run "Create a REST API with user authentication using JWT tokens"
```

**Expected Flow:**
1. Codex implements the initial REST API with authentication
2. Gemini reviews for security best practices and SOLID principles
3. Claude implements the feedback and improvements

### Example 2: Implement a Data Structure

```bash
./ai-orchestrator run "Implement a binary search tree with insert, delete, and search operations" --workflow thorough
```

**Expected Flow:**
1. Codex creates initial implementation
2. Copilot suggests optimizations
3. Gemini reviews data structure design
4. Claude implements improvements
5. Gemini re-reviews

### Example 3: Quick Implementation

```bash
./ai-orchestrator run "Create a function to validate email addresses" --workflow quick
```

**Expected Flow:**
1. Codex implements quickly (no review cycle)

## Advanced Usage

### Specifying Maximum Iterations

```bash
./ai-orchestrator run "Refactor the authentication module" --max-iterations 5
```

### Using Specific Output Directory

```bash
./ai-orchestrator run "Create a CLI tool for file processing" --output ./my-project
```

### Verbose Mode for Debugging

```bash
./ai-orchestrator run "Fix the memory leak in the caching layer" --verbose
```

### Dry Run (See Execution Plan)

```bash
./ai-orchestrator run "Optimize database queries" --dry-run
```

## Configuration Examples

### Custom Workflow

Edit `config/agents.yaml`:

```yaml
workflows:
  security-focused:
    - agent: "codex"
      task: "implement"
      description: "Initial implementation"

    - agent: "gemini"
      task: "review"
      description: "Security audit"

    - agent: "gemini"
      task: "review"
      description: "Second security pass"

    - agent: "claude"
      task: "refine"
      description: "Implement security improvements"
```

Use it:

```bash
./ai-orchestrator run "Create payment processing system" --workflow security-focused
```

### Disable Specific Agent

Edit `config/agents.yaml`:

```yaml
agents:
  copilot:
    enabled: false  # Temporarily disable Copilot
```

## Sample Task Categories

### 1. New Feature Implementation

```bash
./ai-orchestrator run "Add a caching layer using Redis with TTL support"
./ai-orchestrator run "Implement OAuth2 authentication with Google and GitHub"
./ai-orchestrator run "Create a background job queue using Celery"
```

### 2. Code Refactoring

```bash
./ai-orchestrator run "Refactor the user service to follow SOLID principles" --workflow review-only
./ai-orchestrator run "Extract common functionality into reusable utilities"
./ai-orchestrator run "Improve error handling across the application"
```

### 3. Bug Fixes

```bash
./ai-orchestrator run "Fix the race condition in the order processing system"
./ai-orchestrator run "Resolve memory leak in the connection pool"
./ai-orchestrator run "Fix SQL injection vulnerability in search endpoint"
```

### 4. Testing

```bash
./ai-orchestrator run "Write comprehensive unit tests for the authentication module"
./ai-orchestrator run "Add integration tests for the payment processing workflow"
./ai-orchestrator run "Create end-to-end tests for user registration flow"
```

### 5. Documentation

```bash
./ai-orchestrator run "Generate API documentation with examples" --workflow document
./ai-orchestrator run "Create user guide for the CLI tool"
./ai-orchestrator run "Document the deployment process with diagrams"
```

## CLI Commands Reference

### Run a Task

```bash
./ai-orchestrator run <task> [options]
```

Options:
- `--workflow, -w`: Workflow to use (default, quick, thorough, etc.)
- `--config, -c`: Path to configuration file
- `--max-iterations, -m`: Maximum refinement iterations
- `--output, -o`: Output directory
- `--verbose, -v`: Enable verbose logging
- `--dry-run`: Show execution plan without running

### List Available Agents

```bash
./ai-orchestrator agents
```

### List Available Workflows

```bash
./ai-orchestrator workflows
```

### Validate Configuration

```bash
./ai-orchestrator validate
```

### Show Version

```bash
./ai-orchestrator version
```

## Expected Output Examples

### Successful Execution

```
╭─────────────────────────────────────────────╮
│ AI Orchestrator                             │
│ Task: Create a REST API with authentication │
│ Workflow: default                           │
╰─────────────────────────────────────────────╯

Available agents: codex, gemini, claude

Starting execution...

Iteration 1:
  ✓ codex - implement
     Files modified: 3
  ✓ gemini - review
     Suggestions: 5
  ✓ claude - refine
     Files modified: 3

Iteration 2:
  ✓ codex - implement
  ✓ gemini - review
     Suggestions: 1
  ✓ claude - refine

Execution complete! ✓

Task completed successfully! ✓
```

### Agent Availability Check

```
╭──────────────────────────────────────────────────────╮
│                    AI Agents                         │
├─────────┬──────────────┬────────────┬────────────────╯
│ Agent   │ Status       │ Command    │ Role           │
├─────────┼──────────────┼────────────┼─────────────────
│ codex   │ ✓ Available  │ codex      │ implementation │
│ gemini  │ ✓ Available  │ gemini-cli │ review         │
│ claude  │ ✓ Available  │ claude     │ refinement     │ 
│ copilot │ ○ Disabled   │ gh         │ suggestions    │
╰─────────┴──────────────┴────────────┴─────────────────
```

## Tips and Best Practices

### 1. Start with Dry Run

Before running a complex task, use `--dry-run` to see the execution plan:

```bash
./ai-orchestrator run "Complex task" --dry-run
```

### 2. Use Appropriate Workflows

- `quick`: Simple tasks, no review needed
- `default`: Standard implementation-review-refine cycle
- `thorough`: Multiple review passes for critical code
- `review-only`: For existing code that needs improvement

### 3. Monitor Logs

Check `ai-orchestrator.log` for detailed execution information:

```bash
tail -f ai-orchestrator.log
```

### 4. Validate Configuration

After modifying configuration, validate it:

```bash
./ai-orchestrator validate
```

### 5. Iterative Refinement

Use `--max-iterations` to control refinement depth:
- 1-2 iterations: Quick tasks
- 3-4 iterations: Standard tasks
- 5+ iterations: Complex, critical code

## Troubleshooting

### No Agents Available

**Problem:** "No agents available! Please install and configure AI CLI tools."

**Solution:**
1. Install required CLI tools
2. Authenticate with each service
3. Verify with `./ai-orchestrator agents`

### Timeout Errors

**Problem:** Tasks timing out

**Solution:**
1. Increase timeout in `config/agents.yaml`
2. Break task into smaller sub-tasks
3. Use `--max-iterations` to limit refinement

### Configuration Errors

**Problem:** Invalid configuration

**Solution:**
```bash
./ai-orchestrator validate
```

Fix issues reported and retry.

## Real-World Examples

### Example 1: Building a Complete Feature

```bash
# Step 1: Implement core functionality
./ai-orchestrator run "Create a task queue system with priority support"

# Step 2: Add tests
./ai-orchestrator run "Write unit and integration tests for task queue"

# Step 3: Add documentation
./ai-orchestrator run "Generate documentation for task queue API" --workflow document
```

### Example 2: Code Quality Improvement

```bash
# Review existing code
./ai-orchestrator run "Review and refactor src/services/payment.py" --workflow review-only

# Implement improvements
./ai-orchestrator run "Add error handling and input validation to payment service"

# Final security review
./ai-orchestrator run "Security audit of payment processing" --workflow thorough
```

### Example 3: Testing and Quality Assurance

```bash
# Generate tests
./ai-orchestrator run "Create comprehensive test suite for user authentication"

# Review test coverage
./ai-orchestrator run "Review and improve test coverage for authentication module" --workflow review-only
```

# Skills Library

The Skills Library provides reusable skill definitions that help AI agents accomplish specific tasks effectively. Skills are organized by category and can be invoked by any AI agent in the system.

## Available Skills

### Portable AI Collaboration Skills

The standalone [`AI-Collaboration-Skills/`](../AI-Collaboration-Skills/README.md) plugin adds Agent Skills that install across Claude Code, Codex, Cursor, Gemini CLI, and GitHub Copilot CLI.

| Skill | Purpose | Location |
|---|---|---|
| `resume-task` | Verify and continue a task from another agent | `AI-Collaboration-Skills/skills/resume-task/` |
| `inspect-history` | Search prior agent activity without changing files | `AI-Collaboration-Skills/skills/inspect-history/` |
| `collaboration-status` | Report task, session, Git, and checkpoint state | `AI-Collaboration-Skills/skills/collaboration-status/` |
| `create-checkpoint` | Save a durable task milestone and next action | `AI-Collaboration-Skills/skills/create-checkpoint/` |
| `handoff-task` | Prepare verified context for the next agent | `AI-Collaboration-Skills/skills/handoff-task/` |

These portable skills are separate from the project-specific `.claude/skills/` library below and use the plugin's local MCP tools.

### Development Skills

| Skill | Description | Location |
|-------|-------------|----------|
| `react-components` | Build React components with hooks, context, and best practices | `.claude/skills/development/` |
| `rest-api-design` | Design RESTful APIs with proper conventions | `.claude/skills/development/` |
| `python-async` | Write async Python code with proper patterns | `.claude/skills/development/` |
| `database-queries` | Write optimized SQL queries | `.claude/skills/development/` |
| `graphql-development` | Build GraphQL schemas and resolvers | `.claude/skills/development/` |
| `error-handling` | Implement proper error handling patterns | `.claude/skills/development/` |

### Testing Skills

| Skill | Description | Location |
|-------|-------------|----------|
| `unit-testing` | Write comprehensive unit tests | `.claude/skills/testing/` |
| `integration-testing` | Create integration tests for APIs and services | `.claude/skills/testing/` |
| `test-driven-development` | Follow TDD methodology | `.claude/skills/testing/` |
| `performance-testing` | Write load and performance tests | `.claude/skills/testing/` |

### Security Skills

| Skill | Description | Location |
|-------|-------------|----------|
| `input-validation` | Validate and sanitize user inputs | `.claude/skills/security/` |
| `authentication` | Implement secure auth patterns | `.claude/skills/security/` |
| `secure-coding` | Follow secure coding practices | `.claude/skills/security/` |
| `vulnerability-assessment` | Assess and fix vulnerabilities | `.claude/skills/security/` |

### DevOps Skills

| Skill | Description | Location |
|-------|-------------|----------|
| `docker-containerization` | Create optimized Docker images | `.claude/skills/devops/` |
| `ci-cd-pipelines` | Build CI/CD workflows | `.claude/skills/devops/` |
| `kubernetes-deployment` | Deploy to Kubernetes clusters | `.claude/skills/devops/` |

### AI/ML Skills

| Skill | Description | Location |
|-------|-------------|----------|
| `embeddings-retrieval` | Work with embeddings and vector search | `.claude/skills/ai-ml/` |
| `llm-integration` | Integrate LLMs into applications | `.claude/skills/ai-ml/` |
| `rag-pipeline` | Build RAG pipelines | `.claude/skills/ai-ml/` |

### Documentation Skills

| Skill | Description | Location |
|-------|-------------|----------|
| `api-documentation` | Generate OpenAPI/Swagger docs | `.claude/skills/documentation/` |
| `architecture-docs` | Create architecture documentation | `.claude/skills/documentation/` |
| `code-documentation` | Write code comments and docstrings | `.claude/skills/documentation/` |

## Skill Structure

Each skill is defined in a markdown file with the following structure:

```markdown
# Skill Name

## Purpose
Brief description of what the skill does.

## Triggers
Keywords that activate this skill.

## Steps
1. Step one
2. Step two
3. Step three

## Examples
Example usage and code patterns.

## Best Practices
Guidelines for effective use.

## Related Skills
Links to other relevant skills.
```

## Using Skills

### With Claude
Skills are automatically available based on context:
```bash
claude "Create a React component with proper testing"
# Automatically uses: react-components, unit-testing
```

### With Orchestrator
```python
from orchestrator.core import OrchestratorEngine

engine = OrchestratorEngine()
result = engine.execute_task(
    "Build a REST API with JWT authentication",
    skills=["rest-api-design", "authentication"]
)
```

### With Agentic Team
Skills are available to all team roles:
```python
from agentic_team import AgenticTeamEngine

engine = AgenticTeamEngine()
result = engine.execute_task(
    "Create comprehensive test suite",
    # QA Engineer role has access to testing skills
)
```

## Creating Custom Skills

### Step 1: Create Skill File
Create a new markdown file in the appropriate category directory:
```bash
touch .claude/skills/development/my-skill.md
```

### Step 2: Define Skill Structure
```markdown
# My Custom Skill

## Purpose
What this skill accomplishes.

## Triggers
- keyword1
- keyword2
- phrase that triggers this skill

## Steps
1. First step with detailed instructions
2. Second step
3. Final step with verification

## Examples
### Example 1: Basic Usage
```python
# Code example here
```

### Example 2: Advanced Usage
```python
# More complex example
```

## Best Practices
- Practice one
- Practice two

## Common Pitfalls
- Avoid this mistake
- Watch out for this issue

## Related Skills
- [Related Skill 1](./related-skill.md)
- [Related Skill 2](../other-category/skill.md)
```

### Step 3: Test the Skill
Invoke the skill in a task to verify it works:
```bash
claude "Use my-skill to accomplish this task"
```

## Skill Categories

### Development
Skills for writing production code:
- Component development
- API design
- Database operations
- Async programming

### Testing
Skills for quality assurance:
- Unit testing
- Integration testing
- TDD methodology
- Performance testing

### Security
Skills for secure development:
- Input validation
- Authentication
- Secure coding
- Vulnerability assessment

### DevOps
Skills for deployment and operations:
- Containerization
- CI/CD pipelines
- Kubernetes
- Infrastructure as code

### AI/ML
Skills for AI and machine learning:
- Embeddings and vectors
- LLM integration
- RAG pipelines
- Model optimization

### Documentation
Skills for technical writing:
- API documentation
- Architecture docs
- Code documentation
- README templates

## Best Practices

1. **Keep skills focused**: Each skill should do one thing well
2. **Include examples**: Concrete examples help agents understand usage
3. **Document pitfalls**: Common mistakes help avoid errors
4. **Link related skills**: Help agents discover complementary skills
5. **Update regularly**: Keep skills current with best practices

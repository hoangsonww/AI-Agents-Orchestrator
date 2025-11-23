# Contributing to AI Orchestrator

Thank you for your interest in contributing to AI Orchestrator! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- pip and virtualenv

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/your-username/ai-orchestrator.git
cd ai-orchestrator
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
make install-dev
# or
pip install -e ".[dev]"
```

4. **Install pre-commit hooks**

```bash
pre-commit install
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or changes

### 2. Make Changes

- Write clear, concise code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Code Quality

Before committing, ensure your code passes all checks:

```bash
# Format code
make format

# Run linters
make lint

# Run type checking
make type-check

# Run tests
make test

# Run all checks
make all
```

### 4. Commit Changes

We follow conventional commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

Example:
```
feat(adapters): Add support for new AI agent

- Implement new adapter for Agent X
- Add configuration options
- Add comprehensive tests

Closes #123
```

### 5. Push and Create Pull Request

```bash
git push origin your-branch-name
```

Then create a Pull Request on GitHub.

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch

### Pull Request Description

Include:
- **What**: Brief description of changes
- **Why**: Reason for changes
- **How**: Technical details of implementation
- **Testing**: How changes were tested
- **Screenshots**: If applicable

### Review Process

1. Automated checks must pass (CI/CD)
2. At least one maintainer review required
3. Address all review comments
4. Keep PR updated with main branch

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to all public functions/classes

### Type Hints

```python
def process_task(
    task: str,
    workflow: str = "default",
    max_iterations: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process a task using specified workflow.

    Args:
        task: Task description
        workflow: Workflow name (default: "default")
        max_iterations: Maximum iterations (optional)

    Returns:
        Dictionary containing results

    Raises:
        ValueError: If task is invalid
    """
    pass
```

### Testing

- Write unit tests for all new code
- Aim for >80% code coverage
- Use meaningful test names
- Test edge cases and error conditions

```python
def test_task_validation_rejects_empty_task() -> None:
    """Test that empty tasks are rejected."""
    with pytest.raises(ValidationError):
        validate_task("")
```

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Update relevant docs in `docs/` directory
- Include examples where appropriate

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_orchestrator.py

# Specific test
pytest tests/test_orchestrator.py::TestOrchestrator::test_execute_task

# With coverage
pytest --cov

# Integration tests only
pytest -m integration

# Unit tests only
pytest -m "unit or not integration"
```

### Writing Tests

- Use pytest fixtures for setup/teardown
- Mock external dependencies
- Test both success and failure cases
- Use parametrize for multiple test cases

```python
@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return Orchestrator(config_path="tests/fixtures/config.yaml")

@pytest.mark.parametrize("workflow,expected", [
    ("default", 3),
    ("quick", 1),
    ("thorough", 5),
])
def test_workflow_steps(workflow, expected):
    """Test workflow step counts."""
    steps = get_workflow_steps(workflow)
    assert len(steps) == expected
```

## Adding New Features

### New AI Agent Adapter

1. Create adapter in `adapters/your_agent_adapter.py`
2. Extend `BaseAdapter`
3. Implement required methods
4. Add configuration in `config/agents.yaml`
5. Add tests in `tests/test_adapters.py`
6. Update documentation

### New Workflow

1. Define workflow in `config/agents.yaml`
2. Test workflow execution
3. Add examples to documentation
4. Add integration test

## Documentation

### Building Documentation

```bash
cd docs
make html
```

### Documentation Structure

- `README.md` - Main project README
- `docs/architecture.md` - Architecture overview
- `docs/interactive-shell.md` - Shell usage guide
- `docs/adding-agents.md` - Guide for adding agents
- `docs/workflows.md` - Workflow configuration

## Release Process

Maintainers only:

1. Update version in `setup.py` and `pyproject.toml`
2. Update CHANGELOG.md
3. Create release branch
4. Tag release: `git tag -a v1.0.0 -m "Release 1.0.0"`
5. Push tag: `git push origin v1.0.0`
6. GitHub Actions will create release and publish to PyPI

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Security**: Email security@example.com

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- CHANGELOG.md
- Release notes

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

Thank you for contributing! 🎉

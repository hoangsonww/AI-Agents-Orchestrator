.PHONY: help install install-dev test test-unit test-integration test-coverage lint format type-check security clean build docker-build docker-run docs pre-commit

help:
	@echo "Available commands:"
	@echo "  install          - Install production dependencies"
	@echo "  install-dev      - Install development dependencies"
	@echo "  test             - Run all tests"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-coverage    - Run tests with coverage report"
	@echo "  lint             - Run all linters"
	@echo "  format           - Format code with black and isort"
	@echo "  type-check       - Run mypy type checking"
	@echo "  security         - Run security checks (bandit, safety)"
	@echo "  clean            - Remove build artifacts and cache"
	@echo "  build            - Build distribution packages"
	@echo "  docker-build     - Build Docker image"
	@echo "  docker-run       - Run Docker container"
	@echo "  docs             - Generate documentation"
	@echo "  pre-commit       - Run pre-commit hooks on all files"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m "unit or not integration"

test-integration:
	pytest tests/ -v -m integration

test-coverage:
	pytest tests/ -v --cov --cov-report=term-missing --cov-report=html

lint:
	flake8 orchestrator adapters tests
	pylint orchestrator adapters

format:
	black orchestrator adapters tests
	isort orchestrator adapters tests

type-check:
	mypy orchestrator adapters

security:
	bandit -r orchestrator adapters -c pyproject.toml
	safety check --json

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf build dist .coverage htmlcov .pytest_cache .mypy_cache

build: clean
	python -m build

docker-build:
	docker build -t ai-orchestrator:latest .

docker-run:
	docker run -it --rm ai-orchestrator:latest

docs:
	cd docs && make html

pre-commit:
	pre-commit run --all-files

all: format lint type-check test-coverage security

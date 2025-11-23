#!/bin/bash
# Test script for AI Orchestrator

set -e

echo "==================================="
echo "Running AI Orchestrator Tests"
echo "==================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "1. Running unit tests..."
pytest tests/ -v -m "unit or not integration" --cov=orchestrator --cov=adapters
echo "✓ Unit tests passed"
echo ""

echo "2. Running linters..."
echo "  - Black..."
black --check orchestrator adapters tests || true
echo "  - isort..."
isort --check-only orchestrator adapters tests || true
echo "  - Flake8..."
flake8 orchestrator adapters tests || true
echo "✓ Linting complete"
echo ""

echo "3. Running type checks..."
mypy orchestrator adapters --ignore-missing-imports || true
echo "✓ Type checking complete"
echo ""

echo "4. Running security checks..."
bandit -r orchestrator adapters -c pyproject.toml || true
echo "✓ Security scan complete"
echo ""

echo "==================================="
echo "All Tests Complete!"
echo "==================================="

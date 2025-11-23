#!/bin/bash
# Installation script for AI Orchestrator

set -e

echo "==================================="
echo "AI Orchestrator Installation"
echo "==================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.8+ is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip wheel setuptools
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Install in development mode
echo "Installing AI Orchestrator..."
pip install -e .
echo "✓ AI Orchestrator installed"
echo ""

# Setup pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo "Setting up pre-commit hooks..."
    pre-commit install
    echo "✓ Pre-commit hooks installed"
    echo ""
fi

# Create directories
echo "Creating directories..."
mkdir -p output workspace reports sessions logs
echo "✓ Directories created"
echo ""

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  Please edit .env to configure your settings"
    echo ""
fi

# Run validation
echo "Validating installation..."
if ./ai-orchestrator validate; then
    echo "✓ Installation validated"
else
    echo "⚠️  Validation failed. Please check configuration."
fi
echo ""

echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run './ai-orchestrator agents' to check agent availability"
echo "3. Run './ai-orchestrator shell' to start interactive mode"
echo ""
echo "For help: ./ai-orchestrator --help"
echo ""

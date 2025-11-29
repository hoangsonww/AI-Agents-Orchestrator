#!/bin/bash
# Setup script for AI Orchestrator environment

set -e

echo "=== AI Orchestrator Environment Setup ==="
echo ""

# Check if NVM is installed
if [ ! -d "$HOME/.nvm" ]; then
    echo "❌ NVM not found. Please install NVM first:"
    echo "   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    exit 1
fi

# Load NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "✓ NVM loaded"

# Install Node.js v20 if not present
if ! nvm list | grep -q "v20"; then
    echo "Installing Node.js v20..."
    nvm install 20
else
    echo "✓ Node.js v20 already installed"
fi

# Use Node.js v20
nvm use 20
nvm alias default 20

echo "✓ Using Node.js $(node --version)"

# Install/Update AI CLI tools
echo ""
echo "Installing AI CLI tools..."

# Install Codex
if ! npm list -g @openai/codex &>/dev/null; then
    echo "Installing @openai/codex..."
    npm install -g @openai/codex
else
    echo "✓ Codex already installed"
fi

# Install Gemini CLI
if ! npm list -g @google/gemini-cli &>/dev/null; then
    echo "Installing @google/gemini-cli..."
    npm install -g @google/gemini-cli
else
    echo "✓ Gemini CLI already installed"
fi

# Install Claude CLI (if available via npm)
if ! npm list -g @anthropic/claude-cli &>/dev/null; then
    echo "Checking for Claude CLI..."
    if npm view @anthropic/claude-cli &>/dev/null; then
        npm install -g @anthropic/claude-cli
    else
        echo "ℹ  Claude CLI not available via npm, please install manually"
    fi
else
    echo "✓ Claude CLI already installed"
fi

echo ""
echo "Verifying installations..."
echo ""

# Verify each CLI
if command -v codex &>/dev/null; then
    echo "✓ codex: $(which codex)"
else
    echo "❌ codex not found"
fi

if command -v gemini &>/dev/null; then
    echo "✓ gemini: $(which gemini)"
    gemini --version
else
    echo "❌ gemini not found"
fi

if command -v claude &>/dev/null; then
    echo "✓ claude: $(which claude)"
else
    echo "⚠  claude not found - install manually"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Add this to your ~/.bashrc or ~/.zshrc to always use Node v20:"
echo 'export NVM_DIR="$HOME/.nvm"'
echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"'
echo 'nvm use 20 &>/dev/null'
echo ""
echo "Now you can run:"
echo "  ./ai-orchestrator shell"
echo "  ./ai-orchestrator run \"your task\""

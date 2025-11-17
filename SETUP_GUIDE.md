# Setup Guide - Installing AI CLI Tools

**IMPORTANT**: Before using the AI Orchestrator, you need to install and authenticate with the CLI tools you want to use.

## 📋 Prerequisites

The AI Orchestrator coordinates these CLI tools:
- **Claude Code** (command: `claude`)
- **Codex** (command: `codex`)
- **Gemini** (command: `gemini`)
- **GitHub Copilot CLI** (command: `gh copilot`)

You need **at least one** of these installed to use the orchestrator.

## 🔧 Installing Each CLI Tool

### 1. Claude Code CLI

**Install:**
```bash
# Follow Claude Code installation instructions from Anthropic
# Visit: https://docs.claude.com/claude-code
```

**Authenticate:**
```bash
claude auth login
```

**Verify:**
```bash
claude --version
# Should show version info

# Test it works
claude --message "Hello, Claude!"
```

### 2. Codex CLI

**Install:**
```bash
# Install via pip (if available publicly)
pip install openai-codex

# Or follow OpenAI's installation instructions
```

**Authenticate:**
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Or configure via their auth command
codex auth login
```

**Verify:**
```bash
codex --version

# Test it works
echo "Write a hello world function" | codex
```

### 3. Gemini CLI

**Install:**
```bash
# Install Google's Gemini CLI
# Follow Google's installation instructions
pip install google-generativeai

# Or use their CLI tool
```

**Authenticate:**
```bash
# Authenticate with your Google account
gemini auth login

# Or set API key
export GOOGLE_API_KEY="your-api-key"
```

**Verify:**
```bash
gemini --version

# Test it works
gemini --prompt "Hello, Gemini!"
```

### 4. GitHub Copilot CLI

**Install:**
```bash
# First install GitHub CLI
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Then install Copilot extension
gh extension install github/gh-copilot
```

**Authenticate:**
```bash
gh auth login
# Follow the prompts to authenticate
```

**Verify:**
```bash
gh --version
gh copilot --version

# Test it works
gh copilot suggest "write a function"
```

## ✅ Verify All Installations

Run this script to check which tools are available:

```bash
#!/bin/bash

echo "Checking AI CLI Tools..."
echo ""

# Claude
if command -v claude &> /dev/null; then
    echo "✓ Claude Code CLI: INSTALLED"
    claude --version 2>&1 | head -1
else
    echo "✗ Claude Code CLI: NOT FOUND"
fi
echo ""

# Codex
if command -v codex &> /dev/null; then
    echo "✓ Codex CLI: INSTALLED"
    codex --version 2>&1 | head -1
else
    echo "✗ Codex CLI: NOT FOUND"
fi
echo ""

# Gemini
if command -v gemini &> /dev/null; then
    echo "✓ Gemini CLI: INSTALLED"
    gemini --version 2>&1 | head -1
else
    echo "✗ Gemini CLI: NOT FOUND"
fi
echo ""

# GitHub Copilot
if command -v gh &> /dev/null; then
    echo "✓ GitHub CLI: INSTALLED"
    if gh extension list 2>&1 | grep -q copilot; then
        echo "✓ Copilot extension: INSTALLED"
    else
        echo "✗ Copilot extension: NOT INSTALLED"
    fi
else
    echo "✗ GitHub CLI: NOT FOUND"
fi
echo ""

echo "Checking AI Orchestrator..."
if [ -x "./ai-orchestrator" ]; then
    echo "✓ AI Orchestrator: READY"
    ./ai-orchestrator agents
else
    echo "✗ AI Orchestrator: Not executable. Run: chmod +x ai-orchestrator"
fi
```

Save this as `check-tools.sh`, make it executable, and run it:

```bash
chmod +x check-tools.sh
./check-tools.sh
```

## 🎯 Quick Start After Installation

Once you have at least one tool installed:

### 1. Verify AI Orchestrator sees your tools

```bash
./ai-orchestrator agents
```

You should see:
```
                         AI Agents
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Agent   ┃ Status          ┃ Command    ┃ Role           ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ claude  │ ✓ Available     │ claude     │ refinement     │
│ codex   │ ✓ Available     │ codex      │ implementation │
│ gemini  │ ✓ Available     │ gemini     │ review         │
└─────────┴─────────────────┴────────────┴────────────────┘
```

### 2. Test with a simple task

```bash
# One-shot mode
./ai-orchestrator run "Create a hello world function" --workflow quick

# Interactive mode
./ai-orchestrator shell
> Create a hello world function
```

## 🔍 Troubleshooting

### "Agent not available" error

**Problem:** `Agent 'claude' not available. Command 'claude' not found.`

**Solution:**
1. Check if the tool is installed: `which claude`
2. If not installed, install it following the instructions above
3. Make sure it's in your PATH
4. Verify authentication: Try running the command directly

### Authentication errors

**Problem:** Tool is installed but fails with auth errors

**Solution:**
```bash
# Claude
claude auth login

# Codex
export OPENAI_API_KEY="your-key"

# Gemini
gemini auth login

# Copilot
gh auth login
```

### Command not found

**Problem:** `bash: claude: command not found`

**Solution:**
1. Install the tool (see installation instructions above)
2. Add to PATH if installed in custom location:
   ```bash
   export PATH=$PATH:/path/to/tool
   ```
3. Restart your terminal

### Tool installed but orchestrator doesn't see it

**Problem:** `which claude` works but orchestrator says not available

**Solution:**
1. Check config: `cat config/agents.yaml`
2. Make sure `enabled: true`
3. Verify command name matches: `command: "claude"`
4. Run validation: `./ai-orchestrator validate`

## 📝 Configuration

If a tool uses a different command name on your system, update `config/agents.yaml`:

```yaml
agents:
  claude:
    enabled: true
    command: "claude"  # ← Change this to match your command
    role: "refinement"
```

## 🎓 Next Steps

After installation:

1. **Test individual tools:**
   ```bash
   claude --message "Test"
   echo "Test" | codex
   gemini --prompt "Test"
   gh copilot suggest "Test"
   ```

2. **Validate configuration:**
   ```bash
   ./ai-orchestrator validate
   ```

3. **Check available agents:**
   ```bash
   ./ai-orchestrator agents
   ```

4. **Try the interactive shell:**
   ```bash
   ./ai-orchestrator shell
   ```

5. **Read the documentation:**
   - [Interactive Shell Guide](docs/interactive-shell.md)
   - [Architecture](docs/architecture.md)
   - [Adding Agents](docs/adding-agents.md)

## ⚠️ Important Notes

1. **You don't need all tools** - The orchestrator works with whatever you have installed
2. **Authentication required** - Each tool needs to be logged in
3. **API costs** - Some tools (Codex, Gemini) may incur API costs
4. **Internet required** - All tools need internet connection
5. **Test individually first** - Make sure each tool works on its own before using the orchestrator

## 💡 Recommended Setup

For the **best experience**, install all tools:

```bash
# Install all tools
claude auth login    # Claude Code
# Set up Codex
gemini auth login    # Gemini
gh auth login        # Copilot
gh extension install github/gh-copilot

# Verify all are working
./ai-orchestrator agents

# Start using!
./ai-orchestrator shell
```

But you can start with **just Claude** if that's what you have:

```bash
# Only Claude installed
./ai-orchestrator agents
# Shows: claude ✓ Available

# Use Claude-only workflow
./ai-orchestrator shell
> Create a REST API
# Works with just Claude!
```

## 🆘 Getting Help

If you run into issues:

1. Check tool installation: `which <tool-name>`
2. Test tool directly: `<tool-name> --version`
3. Verify authentication: Run auth command
4. Check logs: `cat ai-orchestrator.log`
5. Validate config: `./ai-orchestrator validate`
6. Run in verbose mode: `./ai-orchestrator run "task" --verbose`

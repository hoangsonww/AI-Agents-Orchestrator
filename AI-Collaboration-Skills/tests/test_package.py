"""Static package and manifest verification."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_portable_manifests_target_agent_plugins_1() -> None:
    plugin = load("plugin.json")
    mcp = load("mcp.json")
    assert plugin["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert mcp["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    assert plugin["name"] == "ai-collaboration"
    assert mcp["mcpServers"]["ai-collaboration"]["type"] == "stdio"


def test_native_manifests_are_present_and_named_consistently() -> None:
    manifests = [
        ".codex-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        ".cursor-plugin/plugin.json",
        "gemini-extension.json",
    ]
    assert all(load(path)["name"] == "ai-collaboration" for path in manifests)


def test_each_provider_hook_invokes_shared_ingest_script() -> None:
    hook_files = {
        "claude": "adapters/claude/hooks.json",
        "codex": "adapters/codex/hooks.json",
        "cursor": "adapters/cursor/hooks.json",
        "gemini": "hooks/hooks.json",
        "copilot": "com.github.copilot/hooks/hooks.json",
    }
    for provider, relative in hook_files.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "hooks/ingest.py" in text
        assert provider in text


def test_skills_are_complete_and_portable() -> None:
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    assert len(skills) == 5
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\nname:")
        assert "description:" in text
        assert "TODO" not in text


def test_packaged_scripts_are_executable() -> None:
    assert (ROOT / "bin" / "ai-collaboration").stat().st_mode & 0o111
    assert (ROOT / "bin" / "ai-collaboration-mcp").stat().st_mode & 0o111
    assert (ROOT / "hooks" / "ingest.py").stat().st_mode & 0o111


def test_core_has_no_parent_runtime_imports() -> None:
    forbidden = {"orchestrator", "agentic_team", "mcp_server"}
    for source in (ROOT / "ai_collaboration").glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported.intersection(forbidden), source

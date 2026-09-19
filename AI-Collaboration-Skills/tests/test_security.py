"""Tests for payload privacy helpers."""

import json
from pathlib import Path

from ai_collaboration.config import Settings
from ai_collaboration.security import REDACTED, bounded_json, redact, unique_strings


def test_redact_nested_credentials_and_bearer_tokens() -> None:
    value = {
        "api_key": "abc",
        "accessToken": "camel-case-secret",
        "nested": {
            "password": "def",
            "safe": "Bearer abcdefghijklmnop",
            "command": "deploy --token=abc123456789",
        },
        "items": [{"authorization": "secret"}],
    }

    result = redact(value)

    assert result["api_key"] == REDACTED
    assert result["accessToken"] == REDACTED
    assert result["nested"]["password"] == REDACTED
    assert result["nested"]["safe"] == "Bearer [REDACTED]"
    assert result["nested"]["command"] == "deploy --token=[REDACTED]"
    assert result["items"][0]["authorization"] == REDACTED


def test_redact_private_key_block() -> None:
    secret = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
    assert redact(secret) == REDACTED


def test_bounded_json_truncates_large_payload() -> None:
    encoded = bounded_json({"output": "x" * 5000}, 1024)
    decoded = json.loads(encoded)
    assert decoded["truncated"] is True
    assert decoded["original_bytes"] > 1024


def test_bounded_json_remains_valid_with_tiny_limit() -> None:
    assert json.loads(bounded_json({"output": "large"}, 1)) == 0


def test_unique_strings_preserves_order() -> None:
    assert unique_strings(["a", "", "a", None, " b "]) == ["a", "b"]


def test_default_home_is_shared_not_provider_specific(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("AI_COLLABORATION_HOME", raising=False)
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "codex-only"))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "claude-only"))
    assert Settings.load().home == tmp_path / ".ai-collaboration"

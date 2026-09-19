"""Runtime configuration for AI Collaboration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """Resolved local storage settings."""

    home: Path
    database: Path
    objects: Path
    max_payload_bytes: int = 2 * 1024 * 1024
    inline_payload_bytes: int = 4096

    @classmethod
    def load(cls, home: Optional[Path] = None) -> "Settings":
        """Load settings from an explicit path or the environment."""

        configured = home or _configured_home()
        resolved = configured.expanduser().resolve()
        return cls(
            home=resolved,
            database=resolved / "ai-collaboration.db",
            objects=resolved / "objects",
            max_payload_bytes=_positive_int("AI_COLLABORATION_MAX_PAYLOAD_BYTES", 2 * 1024 * 1024),
            inline_payload_bytes=_positive_int("AI_COLLABORATION_INLINE_PAYLOAD_BYTES", 4096),
        )

    def ensure(self) -> None:
        """Create private storage directories if needed."""

        self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.objects.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.home.chmod(0o700)
            self.objects.chmod(0o700)
        except OSError:
            pass


def _configured_home() -> Path:
    value = os.environ.get("AI_COLLABORATION_HOME")
    if value:
        return Path(value)
    return Path.home() / ".ai-collaboration"


def _positive_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default

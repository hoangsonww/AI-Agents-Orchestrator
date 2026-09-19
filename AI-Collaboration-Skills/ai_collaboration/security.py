"""Privacy-preserving normalization helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Mapping

REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(?:^|_)(?:api[_-]?key|authorization|cookie|credential|password|private[_-]?key|secret|token)(?:$|_)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}")
_PEM = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL
)
_NAMED_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|secret|token)"
    r"(\s*(?:=|:)\s*|\s+)([^\s,;]+)"
)
_TOKEN_LITERAL = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
)
_SENSITIVE_NORMALIZED = {
    "apikey",
    "authorization",
    "authtoken",
    "accesstoken",
    "clientsecret",
    "cookie",
    "credential",
    "credentials",
    "password",
    "passwd",
    "privatekey",
    "refreshtoken",
    "secret",
    "token",
}


def redact(value: Any) -> Any:
    """Recursively redact common credential fields and inline secrets."""

    if isinstance(value, Mapping):
        output: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            output[key_text] = REDACTED if _is_sensitive_key(key_text) else redact(item)
        return output
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        redacted = _PEM.sub(REDACTED, value)
        redacted = _BEARER.sub(r"\1" + REDACTED, redacted)
        redacted = _NAMED_SECRET.sub(r"\1\2" + REDACTED, redacted)
        return _TOKEN_LITERAL.sub(REDACTED, redacted)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return bool(_SENSITIVE_KEY.search(key)) or normalized in _SENSITIVE_NORMALIZED


def bounded_json(value: Any, max_bytes: int) -> bytes:
    """Serialize redacted JSON without exceeding the configured storage limit."""

    encoded = json.dumps(redact(value), ensure_ascii=False, sort_keys=True, default=str).encode(
        "utf-8"
    )
    if len(encoded) <= max_bytes:
        return encoded
    marker = json.dumps(
        {
            "truncated": True,
            "original_bytes": len(encoded),
            "preview": encoded[: max(0, max_bytes - 256)].decode("utf-8", errors="replace"),
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(marker) <= max_bytes:
        return marker
    compact = b'{"truncated":true}'
    if len(compact) <= max_bytes:
        return compact
    return b"0"


def unique_strings(values: Iterable[Any]) -> List[str]:
    """Return stable, non-empty unique strings."""

    seen = set()
    output = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output

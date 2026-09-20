"""Fail-open lifecycle hook entry point."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional, Sequence

from .service import CollaborationService


def run(provider: str, event: str, raw: str) -> Dict[str, Any]:
    """Record a hook payload and return a non-mutating hook response."""

    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict):
        payload = {"value": payload}
    CollaborationService().ingest(provider, event, payload)
    return {}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Record an AI Collaboration hook event")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--event", required=True)
    arguments = parser.parse_args(argv)
    try:
        response = run(arguments.provider, arguments.event, sys.stdin.read())
    except Exception:  # Hooks must never interrupt the host agent.
        print("AI Collaboration capture skipped.", file=sys.stderr)
        response = {}
    sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

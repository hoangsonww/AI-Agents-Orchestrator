#!/usr/bin/env python3
"""Shared lifecycle hook launcher."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_collaboration.hook_runner import main  # noqa: E402

raise SystemExit(main())

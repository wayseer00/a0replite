from __future__ import annotations

import time
from typing import Any, Callable, Optional

from core.guardian import audit


def emit(inst: Any, text: str, stream_fn: Callable[[str], None]) -> None:
    """
    Laws 9+10: the sole function in the codebase that writes human-readable output.
    All output must pass through this function. Records emission in S9.
    """
    stream_fn(text)
    if inst is not None:
        try:
            audit.append_event(
                inst,
                "guardian_emission",
                {"length": len(text), "preview": text[:64], "hmmm": ""},
            )
        except Exception:
            pass


def emit_text(text: str, stream_fn: Callable[[str], None]) -> None:
    """Emit without an inst (e.g. during boot before session exists)."""
    stream_fn(text)

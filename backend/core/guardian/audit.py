from __future__ import annotations

import time
from typing import Any, Optional

from core.invariants import require_hmmm


def append_event(inst: Any, event_type: str, payload: dict) -> None:
    """Append an event to PTCA S9 via push_context. Enforces hmmm invariant."""
    require_hmmm(payload, context=f"audit.append_event:{event_type}")
    entry = {
        "event_type": event_type,
        "timestamp": time.time(),
        **payload,
    }
    inst.push_context({"key": f"_audit_{event_type}", "val": entry})


def get_events(inst: Any, event_type: Optional[str] = None) -> list[dict]:
    """Read S9 audit tail."""
    raw_log = inst.audit_tail(n=100)
    if event_type is None:
        return list(raw_log)
    return [
        e for e in raw_log
        if e.get("event_type") == event_type or e.get("type") == event_type
    ]


def has_event(inst: Any, event_type: str) -> bool:
    """Return True if S9 contains at least one event of this type."""
    return len(get_events(inst, event_type)) > 0

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Optional

from core.invariants import require_hmmm


def _hash_event(prev_hash: str, event: dict) -> str:
    """SHA-256 of prev_hash + deterministic JSON of event."""
    payload = prev_hash + json.dumps(event, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def append_event(inst: Any, event_type: str, payload: dict) -> None:
    """
    Append an event to PTCA S9 via push_context.
    Enforces hmmm invariant. Builds SHA-256 hash chain: each event
    commits to the hash of all preceding events.
    """
    require_hmmm(payload, context=f"audit.append_event:{event_type}")

    tail = inst.audit_tail(n=1)
    prev_hash = tail[0].get("audit_hash", "0" * 64) if tail else "0" * 64

    entry = {
        "event_type": event_type,
        "timestamp": time.time(),
        **payload,
    }
    entry["audit_hash"] = _hash_event(prev_hash, entry)

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

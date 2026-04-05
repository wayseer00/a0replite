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
    Append a guardian audit event to PTCA S5 context.
    Enforces hmmm invariant. Builds SHA-256 hash chain: each event
    commits to the hash of all preceding events for tamper evidence.
    Events are stored as S5 context entries with key '_audit_<event_type>'.
    """
    require_hmmm(payload, context=f"audit.append_event:{event_type}")

    existing = _read_context_events(inst)
    prev_hash = existing[-1].get("audit_hash", "0" * 64) if existing else "0" * 64

    entry = {
        "event_type": event_type,
        "timestamp": time.time(),
        **payload,
    }
    entry["audit_hash"] = _hash_event(prev_hash, entry)

    inst.push_context({"key": f"_audit_{event_type}", "val": entry})


def _read_context_events(inst: Any) -> list[dict]:
    """Read all guardian audit events from S5 context entries."""
    context_entries = getattr(inst, "context_entries", None)
    if context_entries is None:
        return []
    events = []
    for entry in context_entries:
        if isinstance(entry, dict) and entry.get("key", "").startswith("_audit_"):
            val = entry.get("val", {})
            if isinstance(val, dict) and "event_type" in val:
                events.append(val)
    return sorted(events, key=lambda e: e.get("timestamp", 0))


def get_events(inst: Any, event_type: Optional[str] = None) -> list[dict]:
    """Read guardian audit events from S5 context entries."""
    all_events = _read_context_events(inst)
    if event_type is None:
        return all_events
    return [
        e for e in all_events
        if e.get("event_type") == event_type
    ]


def has_event(inst: Any, event_type: str) -> bool:
    """Return True if S5 context contains at least one guardian audit event of this type."""
    return len(get_events(inst, event_type)) > 0

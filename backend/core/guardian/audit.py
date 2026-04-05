from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Optional

from core.invariants import require_hmmm

_GUARDIAN_PREFIX = "guardian:"


def _hash_event(prev_hash: str, event: dict) -> str:
    """SHA-256 of prev_hash + deterministic JSON of event."""
    payload = prev_hash + json.dumps(event, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def append_event(inst: Any, event_type: str, payload: dict) -> None:
    """
    Append a guardian audit event to PTCA S9 via s9.record().
    Enforces hmmm invariant. Builds SHA-256 hash chain: each event
    commits to the hash of all preceding events for tamper evidence.
    Event name is prefixed 'guardian:<event_type>' in S9 to namespace
    guardian events from internal ptca events.
    """
    require_hmmm(payload, context=f"audit.append_event:{event_type}")

    existing = get_events(inst)
    prev_hash = existing[-1].get("audit_hash", "0" * 64) if existing else "0" * 64

    entry = {
        "event_type": event_type,
        "timestamp": time.time(),
        **payload,
    }
    entry["audit_hash"] = _hash_event(prev_hash, entry)

    details = {k: v for k, v in entry.items() if k != "event_type"}
    inst.sentinel_state.s9.record(f"{_GUARDIAN_PREFIX}{event_type}", **details)


def get_events(inst: Any, event_type: Optional[str] = None) -> list[dict]:
    """Read guardian audit events from PTCA S9 log."""
    log = inst.sentinel_state.s9.log
    results = []
    for raw in log:
        event_name = raw.get("event", "")
        if not event_name.startswith(_GUARDIAN_PREFIX):
            continue
        actual_type = event_name[len(_GUARDIAN_PREFIX):]
        if event_type is not None and actual_type != event_type:
            continue
        entry = {k: v for k, v in raw.items() if k not in ("ts", "event")}
        entry["event_type"] = actual_type
        results.append(entry)
    return results


def has_event(inst: Any, event_type: str) -> bool:
    """Return True if S9 contains at least one guardian audit event of this type."""
    return len(get_events(inst, event_type)) > 0

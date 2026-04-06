from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

log = logging.getLogger("a0replite.heartbeat")

_start_time: float = time.time()


def _uptime() -> float:
    return time.time() - _start_time


def _get_lifecycle_state(inst: Any) -> str:
    from services.ptca_service import _session_lifecycles
    try:
        session_id = getattr(inst, "session_id", None) or inst.recall("session_id", default=None) or ""
        lc = _session_lifecycles.get(session_id)
        if lc is not None:
            return lc.state.value
    except Exception:
        pass
    try:
        snap = inst.snapshot()
        s6 = snap.get("S6_IDENTITY", {})
        return "active" if s6.get("approved") else "unapproved"
    except Exception:
        return "unknown"


def _get_s8_risk(inst: Any) -> float:
    try:
        return float(inst.sentinel_state.s8.score)
    except Exception:
        try:
            return float(inst.snapshot().get("S8_RISK", {}).get("score", 0.0))
        except Exception:
            return 0.0


def _get_edcm_snapshot(inst: Any) -> Optional[dict]:
    try:
        return inst.recall("last_edcm_snapshot", default=None)
    except Exception:
        return None


def _get_canon_marker_count() -> int:
    try:
        from core.edcm.data_loader import get_canon
        canon = get_canon()
        return sum(len(v) for v in canon.markers_by_metric.values())
    except Exception:
        return -1


def _get_boot_task_summary(inst: Any) -> Optional[str]:
    try:
        log_entries = inst.sentinel_state.s9.log
        for entry in reversed(list(log_entries)):
            event = entry.get("event", "")
            if "boot_task_complete" in event or "task_failed" in event:
                return f"{event} @ {entry.get('ts', '')}"
    except Exception:
        pass
    return None


def _get_last_chat_ts(inst: Any) -> Optional[float]:
    try:
        log_entries = inst.sentinel_state.s9.log
        for entry in reversed(list(log_entries)):
            event = entry.get("event", "")
            if "first_interaction_complete" in event:
                ts = entry.get("ts")
                return float(ts) if ts is not None else None
    except Exception:
        pass
    return None


async def _get_session_count(app: Any) -> int:
    """Return count of active sessions, or -1 on error."""
    try:
        db = getattr(app.state, "db", None)
        if db is None:
            return -1
        count = await db.fetchval("SELECT COUNT(*) FROM chat_sessions")
        return int(count)
    except Exception:
        return -1


async def _check_db(app: Any) -> str:
    """Return 'ok' or 'error: <msg>' and update status registry."""
    from core import status_registry
    try:
        db = getattr(app.state, "db", None)
        if db is None:
            status_registry.record_error("db", "no pool")
            return "error: no pool"
        await db.fetchval("SELECT 1")
        status_registry.record_ok("db")
        return "ok"
    except Exception as exc:
        msg = str(exc)
        status_registry.record_error("db", msg)
        return f"error: {msg}"


def _build_stats(
    inst: Any,
    db_status: str,
    session_count: int,
) -> dict:
    from core import status_registry
    statuses = status_registry.get_all()
    return {
        "ts": time.time(),
        "uptime_secs": round(_uptime(), 1),
        "lifecycle": _get_lifecycle_state(inst),
        "s8_risk": _get_s8_risk(inst),
        "session_count": session_count,
        "db": db_status,
        "grok": statuses.get("grok", "unknown"),
        "github_wayseer00": statuses.get("github_wayseer00", "unknown"),
        "github_vault2": statuses.get("github_vault2", "unknown"),
        "stripe": statuses.get("stripe", "unconfigured"),
        "boot_task": _get_boot_task_summary(inst),
        "last_chat_ts": _get_last_chat_ts(inst),
        "edcm_snapshot": _get_edcm_snapshot(inst),
        "canon_marker_count": _get_canon_marker_count(),
        "hmmm": "",
    }


async def _tick(app: Any) -> None:
    inst = getattr(app.state, "system_inst", None)
    if inst is None:
        log.debug("Heartbeat skipped — system_inst not yet available")
        return

    db_status, session_count = await asyncio.gather(
        _check_db(app),
        _get_session_count(app),
        return_exceptions=True,
    )

    if isinstance(db_status, Exception):
        db_status = "error"
    if isinstance(session_count, Exception):
        session_count = -1

    stats = _build_stats(inst, str(db_status), int(session_count))

    try:
        from core.guardian.audit import append_event
        append_event(inst, "heartbeat", stats)
        log.debug("Heartbeat written to S9: uptime=%.1fs", stats["uptime_secs"])
    except Exception as exc:
        log.warning("Heartbeat S9 write failed: %s", exc)


async def run_heartbeat_loop(app: Any) -> None:
    global _start_time
    _start_time = time.time()

    try:
        interval = max(10, int(os.environ.get("HEARTBEAT_INTERVAL_SECS", "60")))
    except (ValueError, TypeError):
        log.warning("HEARTBEAT_INTERVAL_SECS is not a valid integer — defaulting to 60s")
        interval = 60
    log.info("Heartbeat loop started (interval=%ds)", interval)

    try:
        await _tick(app)
    except Exception as exc:
        log.error("Initial heartbeat tick error: %s", exc)

    while True:
        await asyncio.sleep(interval)
        try:
            await _tick(app)
        except Exception as exc:
            log.error("Heartbeat tick error: %s", exc)

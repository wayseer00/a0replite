from __future__ import annotations

import os
import time
from typing import Any

_registry: dict[str, Any] = {
    "grok": "unknown",
    "github_wayseer00": "unknown",
    "github_vault2": "unknown",
    "db": "unknown",
    "last_updated": None,
}


def record_ok(service: str) -> None:
    _registry[service] = "ok"
    _registry["last_updated"] = time.time()


def record_unavailable(service: str) -> None:
    """Use for grok — canonical enum is 'ok' | 'unavailable'."""
    _registry[service] = "unavailable"
    _registry["last_updated"] = time.time()


def record_error(service: str) -> None:
    """Use for github_* and db — canonical enum is 'ok' | 'error'."""
    _registry[service] = "error"
    _registry["last_updated"] = time.time()


def get_status(service: str) -> str:
    return str(_registry.get(service, "unknown"))


def get_all() -> dict:
    snap = dict(_registry)

    stripe_ok = bool(
        os.environ.get("STRIPE_SECRET_KEY", "").strip()
        and os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip()
    )
    snap["stripe"] = "ok" if stripe_ok else "unconfigured"

    return snap

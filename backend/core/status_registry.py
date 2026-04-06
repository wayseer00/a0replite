from __future__ import annotations

import os
import time
from typing import Any, Optional

_registry: dict[str, Any] = {
    "grok": "unknown",
    "github_wayseer00": "unknown",
    "github_vault2": "unknown",
    "stripe": "unknown",
    "db": "unknown",
    "last_updated": None,
}


def record_ok(service: str) -> None:
    _registry[service] = "ok"
    _registry["last_updated"] = time.time()


def record_error(service: str, msg: str = "") -> None:
    _registry[service] = f"error: {msg}" if msg else "error"
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

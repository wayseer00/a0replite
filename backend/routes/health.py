from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_system_inst: Optional[object] = None


def set_system_inst(inst: object) -> None:
    global _system_inst
    _system_inst = inst


def _health_payload() -> dict:
    from core.edcm.data_loader import get_canon
    try:
        canon = get_canon()
        doc_count = sum(len(v) for v in canon.markers_by_metric.values())
    except RuntimeError:
        doc_count = -1

    ptca_info: dict = {}
    edcm_info: Optional[dict] = None
    if _system_inst is not None:
        snap = _system_inst.snapshot()
        ptca_info = {
            "s8_risk": snap.get("S8_RISK", {}).get("score", 0.0),
            "epoch": _system_inst.recall("boot_epoch", default=0),
        }
        edcm_info = _system_inst.recall("last_edcm_snapshot", default=None)

    return {
        "status": "ok",
        "ts": time.time(),
        "canon_marker_entries": doc_count,
        "ptca": ptca_info,
        "edcm": edcm_info,
        "hmmm": "",
    }


@router.get("/health")
async def health_bare() -> dict:
    return _health_payload()


@router.get("/api/health")
async def health_api() -> dict:
    return _health_payload()


@router.get("/api/")
async def api_root() -> dict:
    return {
        "service": "a0replite",
        "description": "Grounded AI instance — The Interdependent Way",
        "version": "0.5.0",
        "hmmm": "",
    }

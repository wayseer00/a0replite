from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from core.guardian.audit import get_events
from core.invariants import require_hmmm
from models.guardian import (
    ApproveRequest,
    ApproveResponse,
    AuditResponse,
    RevokeRequest,
    RevokeResponse,
    SnapshotResponse,
)

router = APIRouter(prefix="/guardian", tags=["guardian"])


def _get_inst(request: Request):
    """Return the system PTCA instance from app state."""
    inst = getattr(request.app.state, "system_inst", None)
    if inst is None:
        raise HTTPException(status_code=503, detail="System instance not yet booted")
    return inst


@router.get("/snapshot", response_model=SnapshotResponse)
async def snapshot(request: Request) -> SnapshotResponse:
    inst = _get_inst(request)
    return SnapshotResponse(snapshot=inst.snapshot(), hmmm="")


@router.post("/approve", response_model=ApproveResponse)
async def approve(req: ApproveRequest, request: Request) -> ApproveResponse:
    require_hmmm(req.model_dump(), "POST /guardian/approve")
    inst = _get_inst(request)
    inst.approve(reason=req.reason)
    return ApproveResponse(approved=True, reason=req.reason, hmmm=req.hmmm)


@router.post("/revoke", response_model=RevokeResponse)
async def revoke(req: RevokeRequest, request: Request) -> RevokeResponse:
    require_hmmm(req.model_dump(), "POST /guardian/revoke")
    inst = _get_inst(request)
    inst.revoke(reason=req.reason)
    return RevokeResponse(revoked=True, reason=req.reason, hmmm=req.hmmm)


@router.get("/audit", response_model=AuditResponse)
async def audit(request: Request, event_type: Optional[str] = None, n: int = 20) -> AuditResponse:
    inst = _get_inst(request)
    raw_log = inst.audit_tail(n=n)
    if event_type:
        raw_log = [e for e in raw_log if e.get("type") == event_type or e.get("event_type") == event_type]
    return AuditResponse(events=list(raw_log), hmmm="")

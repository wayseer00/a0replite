from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from core.guardian import audit as guardian_audit
from models.guardian import (
    ApproveRequest,
    ApproveResponse,
    AuditResponse,
    RevokeRequest,
    RevokeResponse,
    SnapshotResponse,
)

router = APIRouter(prefix="/guardian", tags=["guardian"])


def _require_operator_auth(x_operator_key: Optional[str] = None) -> None:
    """
    Require a valid operator API key for guardian control endpoints.
    Uses the dedicated GUARDIAN_OPERATOR_KEY secret — never derived from PCEA_IKM.
    Returns 403 for missing or wrong key.
    """
    expected = os.environ.get("GUARDIAN_OPERATOR_KEY", "")
    if not expected or x_operator_key != expected:
        raise HTTPException(
            status_code=403,
            detail="Operator authentication required for guardian control",
        )


def _get_inst(request: Request):
    """Return the system PTCA instance from app state."""
    inst = getattr(request.app.state, "system_inst", None)
    if inst is None:
        raise HTTPException(status_code=503, detail="System instance not yet booted")
    return inst


@router.get("/snapshot", response_model=SnapshotResponse)
async def snapshot(
    request: Request,
    x_operator_key: Optional[str] = Header(default=None),
) -> SnapshotResponse:
    _require_operator_auth(x_operator_key)
    inst = _get_inst(request)
    return SnapshotResponse(snapshot=inst.snapshot(), hmmm="")


@router.post("/approve", response_model=ApproveResponse)
async def approve(
    req: ApproveRequest,
    request: Request,
    x_operator_key: Optional[str] = Header(default=None),
) -> ApproveResponse:
    _require_operator_auth(x_operator_key)
    inst = _get_inst(request)
    inst.approve(reason=req.reason)
    return ApproveResponse(approved=True, reason=req.reason)


@router.post("/revoke", response_model=RevokeResponse)
async def revoke(
    req: RevokeRequest,
    request: Request,
    x_operator_key: Optional[str] = Header(default=None),
) -> RevokeResponse:
    _require_operator_auth(x_operator_key)
    inst = _get_inst(request)
    inst.revoke(reason=req.reason)
    return RevokeResponse(revoked=True, reason=req.reason)


@router.get("/audit", response_model=AuditResponse)
async def audit(
    request: Request,
    x_operator_key: Optional[str] = Header(default=None),
    event_type: Optional[str] = None,
    n: int = 20,
) -> AuditResponse:
    _require_operator_auth(x_operator_key)
    inst = _get_inst(request)
    events = guardian_audit.get_events(inst, event_type=event_type or None)
    return AuditResponse(events=events[-n:], hmmm="")

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.edcm.dual_layer import DualLayerEDCM
from core.guardian.audit import get_events
from core.invariants import require_hmmm
from models.guardian import (
    ApproveRequest,
    ApproveResponse,
    AuditResponse,
    EDCMValidateRequest,
    EDCMValidateResponse,
    RevokeRequest,
    RevokeResponse,
    SnapshotResponse,
)
from services.data_loader import get_parser
from services.ptca_service import get_instance

router = APIRouter(prefix="/guardian", tags=["guardian"])


@router.get("/snapshot", response_model=SnapshotResponse)
async def snapshot() -> SnapshotResponse:
    inst = get_instance()
    return SnapshotResponse(snapshot=inst.snapshot(), hmmm="")


@router.post("/approve", response_model=ApproveResponse)
async def approve(req: ApproveRequest) -> ApproveResponse:
    require_hmmm(req.model_dump(), "POST /guardian/approve")
    inst = get_instance()
    inst.approve(reason=req.reason)
    return ApproveResponse(approved=True, reason=req.reason, hmmm=req.hmmm)


@router.post("/revoke", response_model=RevokeResponse)
async def revoke(req: RevokeRequest) -> RevokeResponse:
    require_hmmm(req.model_dump(), "POST /guardian/revoke")
    inst = get_instance()
    inst.revoke(reason=req.reason)
    return RevokeResponse(revoked=True, reason=req.reason, hmmm=req.hmmm)


@router.get("/audit", response_model=AuditResponse)
async def audit(event_type: str = None, n: int = 20) -> AuditResponse:
    inst = get_instance()
    raw_log = inst.audit_tail(n=n)
    if event_type:
        raw_log = [e for e in raw_log if e.get("type") == event_type or e.get("event_type") == event_type]
    return AuditResponse(events=list(raw_log), hmmm="")


@router.post("/edcm/validate", response_model=EDCMValidateResponse)
async def edcm_validate(req: EDCMValidateRequest) -> EDCMValidateResponse:
    require_hmmm(req.model_dump(), "POST /guardian/edcm/validate")
    parser = get_parser()
    edcm = DualLayerEDCM(parser)
    evaluation = edcm.evaluate(
        document_name=req.document_name,
        response_text=req.response_text,
        context_vector=req.context_vector,
        facts_recalled=req.facts_recalled,
        facts_available=req.facts_available,
        drift_tokens=req.drift_tokens,
        total_tokens=req.total_tokens,
        novel_claims=req.novel_claims,
        total_claims=req.total_claims,
        latency_ms=req.latency_ms,
        baseline_ms=req.baseline_ms,
    )
    return EDCMValidateResponse(evaluation=evaluation, hmmm=req.hmmm)

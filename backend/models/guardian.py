from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class SnapshotResponse(BaseModel):
    snapshot: dict
    hmmm: str = ""


class ApproveRequest(BaseModel):
    reason: str = ""
    hmmm: Optional[str] = None


class RevokeRequest(BaseModel):
    reason: str = ""
    hmmm: Optional[str] = None


class ApproveResponse(BaseModel):
    approved: bool
    reason: str
    hmmm: str = ""


class RevokeResponse(BaseModel):
    revoked: bool
    reason: str
    hmmm: str = ""


class AuditResponse(BaseModel):
    events: list[dict]
    hmmm: str = ""


class EDCMValidateRequest(BaseModel):
    document_name: str
    response_text: str
    context_vector: list[float] = []
    facts_recalled: int = 0
    facts_available: int = 1
    drift_tokens: int = 0
    total_tokens: int = 1
    novel_claims: int = 0
    total_claims: int = 1
    latency_ms: float = 0.0
    baseline_ms: float = 1000.0
    hmmm: str = ""


class EDCMValidateResponse(BaseModel):
    evaluation: dict
    hmmm: str = ""

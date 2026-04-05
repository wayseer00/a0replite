from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SessionCreate(BaseModel):
    user_id: str
    tier: str = "seeker"
    hmmm: str = ""


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    tier: str
    hmmm: str = ""


class MemoryResponse(BaseModel):
    s7_key_count: int
    s8_risk: float
    tier: str
    pcea_epoch: int
    edcm_last: Optional[dict] = None
    hmmm: str = ""

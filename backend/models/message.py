from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatPayload(BaseModel):
    session_id: str
    message: str
    persona: str = "default"
    hmmm: str = ""


class MessageRecord(BaseModel):
    message_id: str
    session_id: str
    role: str
    content: str
    turn_id: Optional[str] = None
    round_id: Optional[str] = None
    edcm_snapshot: Optional[dict] = None
    hmmm: str = ""

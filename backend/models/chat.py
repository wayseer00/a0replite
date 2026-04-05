from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "grok-3"
    stream: bool = False
    hmmm: str = ""


class ChatResponse(BaseModel):
    content: str
    model: str
    hmmm: str = ""


class FanOutRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "grok-3"
    n: int = Field(default=3, ge=1, le=10)
    hmmm: str = ""


class FanOutResponse(BaseModel):
    results: list[str]
    hmmm: str = ""


class DaisyChainStep(BaseModel):
    role: str
    content: str


class DaisyChainRequest(BaseModel):
    steps: list[DaisyChainStep]
    model: str = "grok-3"
    hmmm: str = ""


class DaisyChainResponse(BaseModel):
    result: str
    hmmm: str = ""


class CouncilRequest(BaseModel):
    question: str
    roles: list[str]
    model: str = "grok-3"
    hmmm: str = ""


class CouncilResponse(BaseModel):
    responses: list[dict]
    hmmm: str = ""

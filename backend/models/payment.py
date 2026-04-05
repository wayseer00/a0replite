from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CheckoutPayload(BaseModel):
    tier: str
    user_id: str
    hmmm: str = ""


class CheckoutResponse(BaseModel):
    checkout_url: str
    hmmm: str = ""


class PlanResponse(BaseModel):
    plans: list[dict]
    hmmm: str = ""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str
    customer_email: Optional[str] = None
    hmmm: str = ""


class CheckoutResponse(BaseModel):
    url: str
    hmmm: str = ""


class PaymentIntentRequest(BaseModel):
    amount_cents: int
    currency: str = "usd"
    hmmm: str = ""


class PaymentIntentResponse(BaseModel):
    id: str
    client_secret: str
    hmmm: str = ""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from core.invariants import require_hmmm
from models.payments import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentIntentRequest,
    PaymentIntentResponse,
)
from services.stripe_service import (
    create_checkout_session,
    create_payment_intent,
    verify_webhook,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest) -> CheckoutResponse:
    require_hmmm(req.model_dump(), "POST /payments/checkout")
    url = await create_checkout_session(
        price_id=req.price_id,
        success_url=req.success_url,
        cancel_url=req.cancel_url,
        customer_email=req.customer_email,
    )
    return CheckoutResponse(url=url, hmmm=req.hmmm)


@router.post("/intent", response_model=PaymentIntentResponse)
async def payment_intent(req: PaymentIntentRequest) -> PaymentIntentResponse:
    require_hmmm(req.model_dump(), "POST /payments/intent")
    result = await create_payment_intent(
        amount_cents=req.amount_cents,
        currency=req.currency,
    )
    return PaymentIntentResponse(
        id=result["id"],
        client_secret=result["client_secret"],
        hmmm=req.hmmm,
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)) -> dict:
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    try:
        event = await verify_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook verification failed: {exc}")
    event_type = event.get("type", "unknown")
    return {"received": True, "event_type": event_type, "hmmm": ""}

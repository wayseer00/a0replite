from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from core.invariants import require_hmmm
from models.payment import CheckoutPayload, CheckoutResponse, PlanResponse
from services.stripe_service import create_checkout_session, get_plans, handle_webhook

router = APIRouter(prefix="/api", tags=["payments"])


@router.get("/payments/plans", response_model=PlanResponse)
async def plans() -> PlanResponse:
    return PlanResponse(plans=get_plans(), hmmm="")


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(payload: CheckoutPayload) -> CheckoutResponse:
    require_hmmm(payload.model_dump(), "POST /api/checkout")
    try:
        url = await create_checkout_session(tier=payload.tier, user_id=payload.user_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CheckoutResponse(checkout_url=url, hmmm=payload.hmmm)


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)) -> dict:
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    db = getattr(request.app.state, "db", None)
    try:
        await handle_webhook(payload, stripe_signature, db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook error: {exc}")
    return {"received": True, "hmmm": ""}

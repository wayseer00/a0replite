from __future__ import annotations

import os
from typing import Any, Optional

import stripe


def _stripe_client() -> stripe.Stripe:
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY not set")
    return stripe.Stripe(key)


async def create_checkout_session(
    price_id: str,
    success_url: str,
    cancel_url: str,
    customer_email: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """Create a Stripe Checkout session and return the URL."""
    sc = _stripe_client()
    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if customer_email:
        params["customer_email"] = customer_email
    if metadata:
        params["metadata"] = metadata
    session = sc.checkout.sessions.create(**params)
    return session.url


async def create_payment_intent(
    amount_cents: int,
    currency: str = "usd",
    metadata: Optional[dict] = None,
) -> dict:
    """Create a PaymentIntent and return client_secret + id."""
    sc = _stripe_client()
    intent = sc.payment_intents.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata or {},
    )
    return {"id": intent.id, "client_secret": intent.client_secret}


async def verify_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify and parse a Stripe webhook event."""
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not set")
    event = stripe.WebhookSignature.verify_header(
        payload.decode(), sig_header, secret
    )
    return event

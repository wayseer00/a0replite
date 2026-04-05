from __future__ import annotations

import os
from typing import Any, Optional

import stripe as stripe_lib

_PLANS = [
    {
        "tier": "seeker",
        "name": "Seeker",
        "price": "free",
        "description": "7-day rolling memory. Entry-level access.",
        "memory_policy": "7-day rolling",
    },
    {
        "tier": "operator",
        "name": "Operator",
        "price": "monthly",
        "description": "30-day rolling memory. Full access.",
        "memory_policy": "30-day rolling",
    },
    {
        "tier": "patron",
        "name": "Patron",
        "price": "monthly",
        "description": "60-day rolling memory. Priority access.",
        "memory_policy": "60-day rolling",
    },
    {
        "tier": "founder",
        "name": "Founder",
        "price": "one-time",
        "description": "Permanent memory. Lifetime access.",
        "memory_policy": "permanent",
    },
]

_PRICE_ID_MAP = {
    "operator": "STRIPE_PRICE_OPERATOR",
    "patron": "STRIPE_PRICE_PATRON",
    "founder": "STRIPE_PRICE_FOUNDER",
}


def _client() -> stripe_lib.Stripe:
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY not set")
    return stripe_lib.Stripe(key)


def get_plans() -> list[dict]:
    return list(_PLANS)


async def create_checkout_session(tier: str, user_id: str) -> str:
    """Create a Stripe Checkout session. Returns URL."""
    price_env = _PRICE_ID_MAP.get(tier)
    if not price_env:
        raise ValueError(f"No price configured for tier {tier!r}")
    price_id = os.environ.get(price_env, "")
    if not price_id:
        raise RuntimeError(f"{price_env} not set")

    client = _client()
    base_url = os.environ.get("SITE_URL", "https://www.interdependentway.org")
    mode = "payment" if tier == "founder" else "subscription"
    session = client.checkout.sessions.create(
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/payment/cancel",
        metadata={"user_id": user_id, "tier": tier},
    )
    return session.url


async def handle_webhook(payload: bytes, sig_header: str, db: Any = None) -> None:
    """
    Verify Stripe webhook and handle checkout.session.completed.
    On success: update user tier in DB, clear session expiry for paid tiers.
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not set")

    event = stripe_lib.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=secret,
    )

    if event["type"] == "checkout.session.completed":
        sess = event["data"]["object"]
        meta = sess.get("metadata", {})
        user_id = meta.get("user_id")
        tier = meta.get("tier")
        stripe_session_id = sess.get("id")
        if user_id and tier and db:
            await db.execute(
                """
                INSERT INTO payment_records (payment_id, user_id, tier, stripe_session_id)
                VALUES (gen_random_uuid(), $1, $2, $3)
                """,
                user_id, tier, stripe_session_id,
            )
            await db.execute(
                """
                UPDATE chat_sessions
                SET tier=$1, expires_at=NULL, last_active_at=NOW()
                WHERE user_id=$2
                """,
                tier, user_id,
            )

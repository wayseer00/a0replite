from __future__ import annotations

import base64
import os
import time
import uuid
from typing import Any, Optional

from ptca import PTCAInstance

from core.crypto.session_crypto import SessionCryptoManager
from services.gist_service import set_gist_ids, store_shares

MODEL_ID = "a0replite"
CALLER_ID = "system"
NODE_ID = "a0-node-0"

_instance: Optional[PTCAInstance] = None
_crypto: Optional[SessionCryptoManager] = None


def get_instance() -> PTCAInstance:
    if _instance is None:
        raise RuntimeError("PTCAInstance not yet initialized — boot not complete")
    return _instance


def get_crypto() -> SessionCryptoManager:
    if _crypto is None:
        raise RuntimeError("SessionCryptoManager not yet initialized — boot not complete")
    return _crypto


async def init_ptca_session(ikm: bytes) -> None:
    """
    Initialize PTCA + PCEA for a new session.
    derive → remember boot readings → seal → split → store gists.
    """
    global _instance, _crypto

    session_id = f"session-{uuid.uuid4()}"
    epoch = int(time.time()) // 86400
    key_id = f"key-{epoch}"

    inst = PTCAInstance(
        model_id=MODEL_ID,
        caller_id=CALLER_ID,
        session_id=session_id,
        approved=False,
    )

    inst.remember("boot_epoch", epoch)
    inst.remember("node_id", NODE_ID)
    inst.remember("initialized_at", time.time())

    crypto = SessionCryptoManager(
        ikm=ikm,
        epoch=epoch,
        key_id=key_id,
        node_id=NODE_ID,
    )
    crypto.derive()

    snapshot = inst.snapshot()
    crypto.seal(ptca_snapshot=snapshot, sealed_by=CALLER_ID)

    shares = crypto.split()
    share_a = crypto.get_share_bytes(0)
    share_b = crypto.get_share_bytes(1)

    share_a_b64 = base64.b64encode(share_a).decode()
    share_b_b64 = base64.b64encode(share_b).decode()

    try:
        gist_a, gist_b = await store_shares(share_a, share_b)
        inst.remember("gist_id_a", gist_a)
        inst.remember("gist_id_b", gist_b)
        set_gist_ids(gist_a, gist_b)
    except Exception as exc:
        import sys
        print(f"[a0replite] WARN: gist store failed: {exc}", file=sys.stderr)

    crypto.wipe_live_key()
    crypto.wipe_meta_key()

    inst.remember("seal_counter", crypto._seal_counter)

    _instance = inst
    _crypto = crypto


def push_context(context_update: dict) -> None:
    """Push a context update dict into the PTCA tensor."""
    inst = get_instance()
    inst.push_context(context_update)


def snapshot_state() -> dict:
    """Return a copy of the current PTCA snapshot."""
    return get_instance().snapshot()


def route_action(action: str, payload: dict) -> str:
    """Route an action through S3 routing logic."""
    return get_instance().route(action, payload)

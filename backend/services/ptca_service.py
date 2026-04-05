from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional

from ptca import PTCAInstance

MODEL_ID = "grok-3"
NODE_ID = "a0-node-0"


def _new_session_id() -> str:
    return str(uuid.uuid4())


def _get_tokens() -> tuple[str, str]:
    return (
        os.environ.get("GITHUB_TOKEN_WAYSEER00", ""),
        os.environ.get("GITHUB_TOKEN_VAULT2", ""),
    )


def _get_ikm() -> bytes:
    ikm_hex = os.environ.get("PCEA_IKM", "")
    if len(ikm_hex) >= 64:
        return bytes.fromhex(ikm_hex[:64])
    raise RuntimeError("PCEA_IKM not set or invalid — cannot seal/unseal sessions")


async def create_session(user_id: str, tier: str, db: Any) -> tuple["PTCAInstance", str]:
    """
    Create a new PTCAInstance session, seal it, store in DB.
    Returns (inst, session_id).
    """
    session_id = _new_session_id()
    epoch = int(time.time()) // 86400
    key_id = f"key-{epoch}"

    inst = PTCAInstance(
        model_id=MODEL_ID,
        caller_id=user_id,
        session_id=session_id,
        approved=False,
    )
    inst.remember("user_id", user_id)
    inst.remember("tier", tier)
    inst.remember("created_at", time.time())

    token1, token2 = _get_tokens()
    ikm = _get_ikm()
    snapshot = inst.snapshot()

    from core.crypto.session_crypto import seal_session
    seal_result = await seal_session(
        ptca_snapshot=snapshot,
        ikm=ikm,
        epoch=epoch,
        key_id=key_id,
        guardian_node_id=NODE_ID,
        github_token_1=token1,
        github_token_2=token2,
    )

    expires_at = time.time() + 7 * 86400 if tier == "seeker" else None

    await db.execute(
        """
        INSERT INTO chat_sessions
          (session_id, user_id, tier, pcea_sealed_blob, pcea_wrapped_key,
           pcea_epoch, pcea_key_id, pcea_gist_id_1, pcea_gist_id_2, expires_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
        session_id,
        user_id,
        tier,
        seal_result["sealed_blob"].encode(),
        seal_result["wrapped_key"].encode(),
        epoch,
        key_id,
        seal_result["gist_id_1"],
        seal_result["gist_id_2"],
        expires_at,
    )

    return inst, session_id


async def restore_session(session_id: str, db: Any) -> "PTCAInstance":
    """Load and unseal a PTCAInstance from the DB + Gist vault."""
    row = await db.fetchrow(
        "SELECT * FROM chat_sessions WHERE session_id=$1",
        session_id,
    )
    if row is None:
        raise KeyError(f"Session {session_id!r} not found")

    token1, token2 = _get_tokens()
    ikm = _get_ikm()

    from core.crypto.session_crypto import unseal_session
    snapshot = await unseal_session(
        sealed_blob=row["pcea_sealed_blob"].decode(),
        nonce=row.get("pcea_nonce", ""),
        aad=row.get("pcea_aad", f"{row['pcea_epoch']}:{row['pcea_key_id']}:{NODE_ID}"),
        wrapped_key=row["pcea_wrapped_key"].decode(),
        gist_id_1=row["pcea_gist_id_1"],
        gist_id_2=row["pcea_gist_id_2"],
        epoch=row["pcea_epoch"],
        key_id=row["pcea_key_id"],
        guardian_node_id=NODE_ID,
        ikm=ikm,
        github_token_1=token1,
        github_token_2=token2,
        commitment=row.get("pcea_commitment", ""),
    )

    inst = PTCAInstance(
        model_id=MODEL_ID,
        caller_id=row["user_id"],
        session_id=session_id,
        approved=snapshot.get("S6_IDENTITY", {}).get("approved", False),
    )
    memory = snapshot.get("S7_MEMORY", {}).get("store", {})
    for k, v in memory.items():
        inst.remember(k, v)

    return inst


async def persist_session(session_id: str, inst: "PTCAInstance", db: Any) -> None:
    """Seal current PTCA state and update the DB row."""
    epoch = int(time.time()) // 86400
    key_id = f"key-{epoch}"
    token1, token2 = _get_tokens()
    ikm = _get_ikm()

    row = await db.fetchrow(
        "SELECT pcea_gist_id_1, pcea_gist_id_2 FROM chat_sessions WHERE session_id=$1",
        session_id,
    )
    existing_gist_1 = row["pcea_gist_id_1"] if row else None
    existing_gist_2 = row["pcea_gist_id_2"] if row else None

    from core.crypto.session_crypto import seal_session
    seal_result = await seal_session(
        ptca_snapshot=inst.snapshot(),
        ikm=ikm,
        epoch=epoch,
        key_id=key_id,
        guardian_node_id=NODE_ID,
        github_token_1=token1,
        github_token_2=token2,
        existing_gist_id_1=existing_gist_1,
        existing_gist_id_2=existing_gist_2,
    )

    await db.execute(
        """
        UPDATE chat_sessions SET
          pcea_sealed_blob=$1, pcea_wrapped_key=$2, pcea_epoch=$3, pcea_key_id=$4,
          pcea_gist_id_1=$5, pcea_gist_id_2=$6, last_active_at=NOW()
        WHERE session_id=$7
        """,
        seal_result["sealed_blob"].encode(),
        seal_result["wrapped_key"].encode(),
        epoch,
        key_id,
        seal_result["gist_id_1"],
        seal_result["gist_id_2"],
        session_id,
    )

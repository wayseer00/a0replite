from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
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


async def create_session(
    user_id: str,
    tier: str,
    db: Any,
    *,
    approved: bool = False,
) -> tuple["PTCAInstance", str]:
    """
    Create a new PTCAInstance session, seal it, store all PCEA fields in DB.
    Returns (inst, session_id).
    Operator-tier system sessions pass approved=True so S4 gates pass without
    requiring a separate pre_authorize call at startup.
    """
    session_id = _new_session_id()
    epoch = int(time.time()) // 86400
    key_id = f"key-{epoch}"

    inst = PTCAInstance(
        model_id=MODEL_ID,
        caller_id=user_id,
        session_id=session_id,
        approved=approved,
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

    expires_at = (
        datetime.fromtimestamp(time.time() + 7 * 86400, tz=timezone.utc)
        if tier == "seeker"
        else None
    )

    await db.execute(
        """
        INSERT INTO chat_sessions
          (session_id, user_id, tier,
           pcea_sealed_blob, pcea_wrapped_key,
           pcea_epoch, pcea_key_id,
           pcea_gist_id_1, pcea_gist_id_2,
           pcea_nonce, pcea_aad, pcea_commitment,
           expires_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
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
        seal_result["nonce"],
        seal_result["aad"],
        seal_result["commitment"],
        expires_at,
    )

    await db.executemany(
        """
        INSERT INTO pcea_shares
          (session_id, sentinel_id, gist_id, epoch, key_id, index_in_scheme, commitment)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (session_id, sentinel_id, epoch, key_id) DO UPDATE
          SET gist_id=EXCLUDED.gist_id, commitment=EXCLUDED.commitment, updated_at=NOW()
        """,
        [
            (session_id, "wayseer00", seal_result["gist_id_1"], epoch, key_id, 1, seal_result["commitment"]),
            (session_id, "vault2", seal_result["gist_id_2"], epoch, key_id, 2, seal_result["commitment"]),
        ],
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

    nonce = row.get("pcea_nonce") or ""
    aad = row.get("pcea_aad") or f"{row['pcea_epoch']}:{row['pcea_key_id']}:{NODE_ID}"
    commitment = row.get("pcea_commitment") or ""

    from core.crypto.session_crypto import unseal_session
    snapshot = await unseal_session(
        sealed_blob=row["pcea_sealed_blob"].decode(),
        nonce=nonce,
        aad=aad,
        wrapped_key=row["pcea_wrapped_key"].decode(),
        gist_id_1=row["pcea_gist_id_1"],
        gist_id_2=row["pcea_gist_id_2"],
        epoch=row["pcea_epoch"],
        key_id=row["pcea_key_id"],
        guardian_node_id=NODE_ID,
        ikm=ikm,
        github_token_1=token1,
        github_token_2=token2,
        commitment=commitment,
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

    for entry in snapshot.get("S5_CONTEXT", {}).get("entries", []):
        inst.push_context(entry)

    return inst


async def persist_session(session_id: str, inst: "PTCAInstance", db: Any) -> None:
    """Seal current PTCA state and update the DB row with all PCEA fields."""
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
          pcea_sealed_blob=$1, pcea_wrapped_key=$2,
          pcea_epoch=$3, pcea_key_id=$4,
          pcea_gist_id_1=$5, pcea_gist_id_2=$6,
          pcea_nonce=$7, pcea_aad=$8, pcea_commitment=$9,
          last_active_at=NOW()
        WHERE session_id=$10
        """,
        seal_result["sealed_blob"].encode(),
        seal_result["wrapped_key"].encode(),
        epoch,
        key_id,
        seal_result["gist_id_1"],
        seal_result["gist_id_2"],
        seal_result["nonce"],
        seal_result["aad"],
        seal_result["commitment"],
        session_id,
    )

    await db.executemany(
        """
        INSERT INTO pcea_shares
          (session_id, sentinel_id, gist_id, epoch, key_id, index_in_scheme, commitment)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (session_id, sentinel_id, epoch, key_id) DO UPDATE
          SET gist_id=EXCLUDED.gist_id, commitment=EXCLUDED.commitment, updated_at=NOW()
        """,
        [
            (session_id, "wayseer00", seal_result["gist_id_1"], epoch, key_id, 1, seal_result["commitment"]),
            (session_id, "vault2", seal_result["gist_id_2"], epoch, key_id, 2, seal_result["commitment"]),
        ],
    )

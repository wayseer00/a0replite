from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Optional

from guardian_state import (
    derive_keys,
    make_commitment,
    reconstruct_meta_key,
    split_meta_key,
    unseal_live_state,
    verify_commitment,
    wipe,
    wrap_live_key,
    unwrap_live_key,
)
from guardian_state.aead import seal, unseal
from guardian_state.threshold import split_secret, reconstruct_secret
from guardian_state.wrap import WrappedLiveKey

from core.crypto.gist_store import load_share, store_share


async def seal_session(
    ptca_snapshot: dict,
    ikm: bytes,
    epoch: int,
    key_id: str,
    guardian_node_id: str,
    github_token_1: str,
    github_token_2: str,
    existing_gist_id_1: Optional[str] = None,
    existing_gist_id_2: Optional[str] = None,
) -> dict:
    """
    Seal PTCA snapshot with PCEA:
    1. derive_keys → (live_key, meta_key)
    2. seal plaintext with live_key (AES-256-GCM)
    3. wrap_live_key with meta_key
    4. split meta_key 2-of-2 via threshold.split_secret
    5. store shares as private GitHub Gists
    6. make_commitment over shares
    7. wipe live_key and meta_key in finally
    Returns: {sealed_blob, nonce, aad, wrapped_key_b64, gist_id_1, gist_id_2, commitment, epoch, key_id}
    """
    live_key = b""
    meta_key = b""
    try:
        live_key, meta_key = derive_keys(ikm, epoch, key_id, guardian_node_id)

        plaintext = json.dumps(ptca_snapshot, default=str).encode()
        nonce = os.urandom(12)
        aad = f"{epoch}:{key_id}:{guardian_node_id}".encode()
        ciphertext = seal(live_key, nonce, plaintext, aad)

        wrapped: WrappedLiveKey = wrap_live_key(live_key, meta_key, epoch, key_id)

        shares: list[tuple[int, bytes]] = split_secret(meta_key, threshold=2, n=2)
        share0_b64 = base64.b64encode(shares[0][1]).decode()
        share1_b64 = base64.b64encode(shares[1][1]).decode()
        commitment_shares = [
            {"sentinel_id": "gist_wayseer00", "share": shares[0][1], "index": shares[0][0]},
            {"sentinel_id": "gist_vault2", "share": shares[1][1], "index": shares[1][0]},
        ]
        commitment = make_commitment(commitment_shares)

        description = f"a0replite PCEA share — epoch {epoch}"
        gist_id_1 = await store_share(github_token_1, existing_gist_id_1, "gist_wayseer00", share0_b64, description)
        gist_id_2 = await store_share(github_token_2, existing_gist_id_2, "gist_vault2", share1_b64, description)

        return {
            "sealed_blob": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "aad": aad.decode(),
            "wrapped_key": base64.b64encode(wrapped.wrapped_live_key).decode(),
            "wrapped_key_id": wrapped.key_id,
            "gist_id_1": gist_id_1,
            "gist_id_2": gist_id_2,
            "commitment": commitment,
            "epoch": epoch,
            "key_id": key_id,
        }
    finally:
        if live_key:
            wipe(live_key)
        if meta_key:
            wipe(meta_key)


async def unseal_session(
    sealed_blob: str,
    nonce: str,
    aad: str,
    wrapped_key: str,
    gist_id_1: str,
    gist_id_2: str,
    epoch: int,
    key_id: str,
    guardian_node_id: str,
    ikm: bytes,
    github_token_1: str,
    github_token_2: str,
    commitment: str,
) -> dict:
    """
    Unseal a PTCA snapshot from the Gist vault.
    1. Fetch shares from both Gists
    2. Verify commitment
    3. Reconstruct meta_key via threshold.reconstruct_secret
    4. Re-derive keys for unwrapping context
    5. Unwrap live_key using meta_key
    6. Decrypt sealed_blob
    7. Wipe keys in finally
    Returns ptca_snapshot dict.
    """
    live_key = b""
    meta_key = b""
    try:
        share0_bytes = await load_share(github_token_1, gist_id_1, "gist_wayseer00")
        share1_bytes = await load_share(github_token_2, gist_id_2, "gist_vault2")

        if commitment:
            commitment_shares = [
                {"sentinel_id": "gist_wayseer00", "share": share0_bytes, "index": 1},
                {"sentinel_id": "gist_vault2", "share": share1_bytes, "index": 2},
            ]
            if not verify_commitment(commitment_shares, commitment):
                raise ValueError("PCEA commitment verification failed — share integrity compromised")

        meta_key = reconstruct_secret([(1, share0_bytes), (2, share1_bytes)])

        live_key, _ = derive_keys(ikm, epoch, key_id, guardian_node_id)

        wrapped = WrappedLiveKey(
            key_id=key_id,
            epoch=epoch,
            wrapped_live_key=base64.b64decode(wrapped_key),
            wrap_key_hash="",
        )
        live_key = unwrap_live_key(wrapped, meta_key)

        ciphertext = base64.b64decode(sealed_blob)
        nonce_bytes = base64.b64decode(nonce)
        aad_bytes = aad.encode()
        plaintext = unseal(live_key, nonce_bytes, ciphertext, aad_bytes)
        return json.loads(plaintext.decode())
    finally:
        if live_key:
            wipe(live_key)
        if meta_key:
            wipe(meta_key)

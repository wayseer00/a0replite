from __future__ import annotations

import base64
import json
import os
from typing import Optional

from core.crypto.gist_store import create_gist, load_share, store_share

_GIST_ID_A: Optional[str] = None
_GIST_ID_B: Optional[str] = None


def _tokens() -> tuple[str, str]:
    a = os.environ.get("GITHUB_TOKEN_WAYSEER00", "")
    b = os.environ.get("GITHUB_TOKEN_VAULT2", "")
    return a, b


async def store_shares(share_a: bytes, share_b: bytes) -> tuple[str, str]:
    """
    Store Shamir shares as private Gists.
    Returns (gist_id_a, gist_id_b).
    """
    global _GIST_ID_A, _GIST_ID_B
    token_a, token_b = _tokens()

    if not token_a or not token_b:
        raise RuntimeError("GitHub tokens not set (GITHUB_TOKEN_WAYSEER00, GITHUB_TOKEN_VAULT2)")

    b64_a = base64.b64encode(share_a).decode()
    b64_b = base64.b64encode(share_b).decode()

    _GIST_ID_A = await store_share(token_a, _GIST_ID_A, "gist_wayseer00", b64_a)
    _GIST_ID_B = await store_share(token_b, _GIST_ID_B, "gist_vault2", b64_b)
    return _GIST_ID_A, _GIST_ID_B


async def load_shares() -> tuple[bytes, bytes]:
    """Load Shamir shares from Gists. Gist IDs must be set."""
    token_a, token_b = _tokens()
    if not _GIST_ID_A or not _GIST_ID_B:
        raise RuntimeError("Gist IDs not set — shares not yet stored this session")
    share_a = await load_share(token_a, _GIST_ID_A, "gist_wayseer00")
    share_b = await load_share(token_b, _GIST_ID_B, "gist_vault2")
    return share_a, share_b


def set_gist_ids(gid_a: str, gid_b: str) -> None:
    global _GIST_ID_A, _GIST_ID_B
    _GIST_ID_A = gid_a
    _GIST_ID_B = gid_b


def get_gist_ids() -> tuple[Optional[str], Optional[str]]:
    return _GIST_ID_A, _GIST_ID_B

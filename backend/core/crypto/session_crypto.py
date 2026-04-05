from __future__ import annotations

import time
from typing import Any

from guardian_state import (
    LiveState,
    MetaShares,
    SealedState,
    derive_keys,
    reconstruct_meta_key,
    seal_live_state,
    split_meta_key,
    wipe,
)

SENTINEL_A = "wayseer00"
SENTINEL_B = "vault2"


class SessionCryptoManager:
    """
    Manages per-session PCEA lifecycle:
    derive → seal → split → store gists → reconstruct → unseal.
    """

    def __init__(self, ikm: bytes, epoch: int, key_id: str, node_id: str) -> None:
        self._ikm = ikm
        self._epoch = epoch
        self._key_id = key_id
        self._node_id = node_id
        self._live_key: bytes | None = None
        self._meta_key: bytes | None = None
        self._sealed: SealedState | None = None
        self._meta_shares: MetaShares | None = None
        self._seal_counter = 0

    def derive(self) -> None:
        """Derive live_key and meta_key from IKM."""
        self._live_key, self._meta_key = derive_keys(
            self._ikm, self._epoch, self._key_id, self._node_id
        )

    def seal(self, ptca_snapshot: dict, sealed_by: str) -> SealedState:
        """Seal current PTCA snapshot into a SealedState."""
        if self._live_key is None:
            raise RuntimeError("Must call derive() before seal()")
        state = LiveState(
            epoch=self._epoch,
            spiral={},
            cores={},
            density_matrix=None,
            coherence=1.0,
            transport=ptca_snapshot,
            last_renorm=time.time(),
        )
        self._seal_counter += 1
        self._sealed = seal_live_state(
            state,
            self._live_key,
            self._epoch,
            self._key_id,
            self._seal_counter,
            self._node_id,
            sealed_by,
        )
        return self._sealed

    def split(self) -> MetaShares:
        """Split the meta_key 2-of-2 for SENTINEL_A and SENTINEL_B."""
        if self._meta_key is None:
            raise RuntimeError("Must call derive() before split()")
        self._meta_shares = split_meta_key(
            self._meta_key, threshold=2, sentinels=[SENTINEL_A, SENTINEL_B]
        )
        return self._meta_shares

    def get_share_bytes(self, index: int) -> bytes:
        """Return the raw share bytes at position index from the split result."""
        if self._meta_shares is None:
            raise RuntimeError("Must call split() first")
        share_dict = self._meta_shares.shares[index]
        return share_dict["share"]

    def reconstruct(self, share_dicts: list[dict]) -> bytes:
        """Reconstruct meta_key from list of share dicts and the MetaShares commitment."""
        if self._meta_shares is None:
            raise RuntimeError("No meta shares recorded — can only reconstruct from split()")
        return reconstruct_meta_key(share_dicts, self._meta_shares)

    @property
    def sealed_state(self) -> SealedState | None:
        return self._sealed

    def wipe_live_key(self) -> None:
        """Wipe live key from memory after sealing."""
        if self._live_key is not None:
            wipe(self._live_key)
            self._live_key = None

    def wipe_meta_key(self) -> None:
        """Wipe meta key from memory after splitting."""
        if self._meta_key is not None:
            wipe(self._meta_key)
            self._meta_key = None

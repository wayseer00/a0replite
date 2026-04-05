from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx

from core.edcm.zeta_parser import ZetaDocument, ZetaParser

_DATA_DIR = Path(__file__).parent.parent / "data"
_ZIP_PATH = _DATA_DIR / "edcmbone_canon_data_v1.zip"
_CANON_URL = "https://raw.githubusercontent.com/The-Interdependency/edcmbone/master/edcmbone_canon_data_v1.zip"

_parser: Optional[ZetaParser] = None
_zip_bytes: Optional[bytes] = None


async def ensure_canon_data() -> ZetaParser:
    """
    Ensure canonical edcmbone zip is available (on disk or downloaded fresh).
    Returns a fully-loaded ZetaParser instance.
    """
    global _parser, _zip_bytes

    if _parser is not None:
        return _parser

    raw = _load_from_disk()
    if raw is None:
        raw = await _download_zip()
        _save_to_disk(raw)

    _zip_bytes = raw
    _parser = ZetaParser()
    _parser.load_zip(raw)
    return _parser


def _load_from_disk() -> Optional[bytes]:
    if _ZIP_PATH.exists() and _ZIP_PATH.stat().st_size > 0:
        return _ZIP_PATH.read_bytes()
    return None


async def _download_zip() -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_CANON_URL)
        resp.raise_for_status()
        return resp.content


def _save_to_disk(data: bytes) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _ZIP_PATH.write_bytes(data)


def get_parser() -> ZetaParser:
    """Return the already-loaded parser (must call ensure_canon_data first)."""
    if _parser is None:
        raise RuntimeError("Canonical data not yet loaded — call ensure_canon_data() at startup")
    return _parser


def get_document(name: str) -> Optional[ZetaDocument]:
    return get_parser().get(name)


def search_canon(pattern: str) -> list[dict]:
    return get_parser().grep(pattern)

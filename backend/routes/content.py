from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from core.guardian.recovery import quarantine
from services.github import fetch_file

router = APIRouter(prefix="/api", tags=["content"])

_PAGES = [
    "index.html",
    "canon/the_interdependent_way.md",
    "a0precepts.md",
]


@router.get("/content")
async def get_content() -> dict:
    """Fetch canonical page content from wayseer.github.io."""
    token = os.environ.get("GITHUB_TOKEN_WAYSEER00", "")
    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN_WAYSEER00 not configured")

    pages = {}
    for path in _PAGES:
        try:
            content = await fetch_file(path, token)
            pages[path] = content[:8000]
        except Exception as exc:
            quarantine(exc, f"content:fetch:{path}")
            pages[path] = None

    return {"pages": pages, "hmmm": ""}

from __future__ import annotations

import json
import pathlib

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["policy"])

_POLICY_PATH = pathlib.Path(__file__).parent.parent / "policy" / "openai_policy.json"


@router.get("/policy")
async def get_policy() -> JSONResponse:
    """Return the OpenAI policy JSON."""
    if not _POLICY_PATH.exists():
        return JSONResponse(status_code=404, content={"error": "policy not found"})
    data = json.loads(_POLICY_PATH.read_text())
    return JSONResponse(content=data)

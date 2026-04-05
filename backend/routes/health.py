from __future__ import annotations

import os
import time

from fastapi import APIRouter

from services.data_loader import get_parser

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    try:
        parser = get_parser()
        doc_count = len(parser.all_names())
    except RuntimeError:
        doc_count = -1

    return {
        "status": "ok",
        "ts": time.time(),
        "canon_docs": doc_count,
        "hmmm": "",
    }


@router.get("/")
async def root() -> dict:
    return {
        "service": "a0replite",
        "description": "Grounded AI instance — The Interdependent Way",
        "version": "0.1.0",
        "hmmm": "",
    }

from __future__ import annotations

import os
import sys
import time
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.guardian.recovery import quarantine
from core.invariants import InvariantViolation
from core.laws import LawViolation
from core.volatile_task import VolatileTask, get_queue
from routes.chat import router as chat_router
from routes.guardian import router as guardian_router
from routes.health import router as health_router
from routes.payments import router as payments_router
from services.data_loader import ensure_canon_data
from services.ptca_service import init_ptca_session

app = FastAPI(
    title="a0replite",
    description="Grounded AI instance — The Interdependent Way",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router, prefix="/api")
app.include_router(guardian_router, prefix="/api")
app.include_router(payments_router, prefix="/api")


@app.exception_handler(InvariantViolation)
async def invariant_handler(request: Request, exc: InvariantViolation) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "invariant_violation", "detail": str(exc)})


@app.exception_handler(LawViolation)
async def law_handler(request: Request, exc: LawViolation) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": "law_violation", "detail": str(exc)})


def _get_ikm() -> bytes:
    """Load PCEA IKM from environment (32 bytes hex). Never regenerated after first boot."""
    ikm_hex = os.environ.get("PCEA_IKM", "")
    if len(ikm_hex) >= 64:
        return bytes.fromhex(ikm_hex[:64])
    import hashlib
    fallback = hashlib.sha256(b"a0replite-fallback-ikm").digest()
    return fallback


async def _register_boot_tasks() -> None:
    """Register the self-authorizing boot task: website repair → self-delete."""
    from services.website_task import repair_website
    queue = get_queue()
    task = VolatileTask(
        id=f"boot-repair-{uuid.uuid4()}",
        name="website_repair",
        fn=repair_website,
        self_delete=True,
    )
    queue.register(task)
    task_id = task.id

    import asyncio
    async def _run_boot_task() -> None:
        await asyncio.sleep(2)
        await queue.run(task_id)

    asyncio.create_task(_run_boot_task())


@app.on_event("startup")
async def startup_event() -> None:
    """
    Three-step startup:
    1. Load canonical edcmbone data (Zeta parser)
    2. Init PTCA + PCEA session
    3. Register and dispatch autonomous boot tasks
    """
    t0 = time.time()
    print("[a0replite] startup: loading canonical data…", flush=True)

    try:
        await ensure_canon_data()
    except Exception as exc:
        quarantine(exc, "startup:ensure_canon_data")

    try:
        ikm = _get_ikm()
        await init_ptca_session(ikm)
        print(f"[a0replite] PTCA+PCEA session ready in {time.time()-t0:.2f}s", flush=True)
    except Exception as exc:
        quarantine(exc, "startup:init_ptca_session")

    try:
        await _register_boot_tasks()
        print("[a0replite] boot tasks registered and dispatched", flush=True)
    except Exception as exc:
        quarantine(exc, "startup:register_boot_tasks")

    print(f"[a0replite] startup complete in {time.time()-t0:.2f}s", flush=True)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    print("[a0replite] shutdown", flush=True)

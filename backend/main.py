from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("a0replite.main")

_REQUIRED_ENV = [
    "XAI_API_KEY",
    "GITHUB_TOKEN_WAYSEER00",
    "GITHUB_TOKEN_VAULT2",
    "PCEA_IKM",
    "DATABASE_URL",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
]

_RECOMMENDED_ENV = [
    "GUARDIAN_OPERATOR_KEY",
]

_PAYMENTS_ENV = [
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
]


def _check_env() -> None:
    core_required = [k for k in _REQUIRED_ENV if k not in _PAYMENTS_ENV]
    missing_core = [k for k in core_required if not os.environ.get(k, "").strip()]
    if missing_core:
        log.critical("STARTUP FAIL — missing required env vars: %s", ", ".join(missing_core))
        sys.exit(1)
    missing_payments = [k for k in _PAYMENTS_ENV if not os.environ.get(k, "").strip()]
    if missing_payments:
        log.warning(
            "Stripe secrets not configured: %s — payment endpoints will return 503 until set",
            ", ".join(missing_payments),
        )
    for key in _RECOMMENDED_ENV:
        if not os.environ.get(key, "").strip():
            log.warning("Recommended env var not set: %s — guardian endpoints will be unavailable", key)


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


_check_env()

from core.invariants import InvariantViolation
from core.laws import LawViolation
from routes.chat import router as chat_router
from routes.content import router as content_router
from routes.guardian import router as guardian_router
from routes.health import router as health_router
from routes.payments import router as payments_router

app = FastAPI(title="a0replite", version="0.3.0", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.interdependentway.org", "https://interdependentway.org"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(content_router)
app.include_router(payments_router)
app.include_router(guardian_router)


@app.exception_handler(InvariantViolation)
async def invariant_handler(request: Request, exc: InvariantViolation) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "invariant_violation", "detail": str(exc)})


@app.exception_handler(LawViolation)
async def law_handler(request: Request, exc: LawViolation) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": "law_violation", "detail": str(exc)})


@app.on_event("startup")
async def startup() -> None:
    db_url = _normalize_db_url(os.environ["DATABASE_URL"])
    app.state.db = await asyncpg.create_pool(db_url, min_size=2, max_size=10, command_timeout=30)
    log.info("DB pool created")

    await _run_migrations()

    from core.edcm.data_loader import load_canonical_data, CanonLoadError
    try:
        load_canonical_data()
        log.info("EDCM canonical data loaded")
    except CanonLoadError as exc:
        log.critical("EDCM canon load failed — aborting: %s", exc)
        sys.exit(1)

    await _boot_system_instance()


@app.on_event("shutdown")
async def shutdown() -> None:
    if hasattr(app.state, "db"):
        await app.state.db.close()
    log.info("a0replite shutdown")


async def _run_migrations() -> None:
    import pathlib

    alembic_ini = pathlib.Path(__file__).parent / "alembic.ini"
    if not alembic_ini.exists():
        log.warning("alembic.ini not found — skipping migrations")
        return

    db_url = _normalize_db_url(os.environ["DATABASE_URL"])
    env = {**os.environ, "DATABASE_URL": db_url}
    backend_dir = str(pathlib.Path(__file__).parent)

    try:
        env["PYTHONPATH"] = f"/home/runner/workspace:/home/runner/workspace/backend"
        result = await asyncio.create_subprocess_exec(
            "python3", "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=backend_dir,
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=60)
        if result.returncode != 0:
            log.error("Alembic failed (rc=%d): %s", result.returncode, stderr.decode())
        else:
            log.info("Alembic migrations applied: %s", stdout.decode().strip() or "up to date")
    except asyncio.TimeoutError:
        log.error("Alembic migration timed out after 60s")
    except Exception as exc:
        log.error("Alembic migration error: %s", exc)


async def _boot_system_instance() -> None:
    from ptca import PTCAInstance
    from core.grok_adapter import make_grok_call_fn
    from routes.health import set_system_inst

    SYSTEM_USER = "a0-system"
    db = app.state.db

    existing_row = await db.fetchrow(
        "SELECT session_id FROM chat_sessions WHERE user_id=$1 ORDER BY created_at ASC LIMIT 1",
        SYSTEM_USER,
    )

    if existing_row:
        from services.ptca_service import restore_session
        try:
            inst = await restore_session(str(existing_row["session_id"]), db)
            log.info("System PTCAInstance restored from DB")
        except Exception as exc:
            log.warning("Could not restore system session (%s) — creating fresh", exc)
            inst, _ = await _create_system_inst(SYSTEM_USER, db)
    else:
        inst, _ = await _create_system_inst(SYSTEM_USER, db)

    set_system_inst(inst)
    inst.remember("boot_epoch", int(time.time()) // 86400)

    github_token = os.environ.get("GITHUB_TOKEN_WAYSEER00", "")
    api_key = os.environ.get("XAI_API_KEY", "")
    grok_text_fn = make_grok_call_fn(api_key)

    app.state.system_inst = inst

    async def _run_background_tasks() -> None:
        from services.boot import run_boot_sequence
        from core.boot_task import make_boot_task
        from core.volatile_task import get_queue
        try:
            await run_boot_sequence(inst, grok_text_fn, github_token)
            log.info("Boot sequence complete")
        except Exception as exc:
            log.error("Boot sequence error: %s", exc)

        boot_task = make_boot_task(inst, grok_text_fn, github_token)
        queue = get_queue()
        queue.register(boot_task)
        await queue.run(boot_task.id, inst)

    asyncio.create_task(_run_background_tasks())


async def _create_system_inst(user_id: str, db):
    from services.ptca_service import create_session
    inst, session_id = await create_session(
        user_id=user_id, tier="operator", db=db, approved=True
    )
    log.info("System PTCAInstance created: %s", session_id)
    return inst, session_id

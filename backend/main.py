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
]


def _check_env() -> None:
    missing = [k for k in _REQUIRED_ENV if not os.environ.get(k, "").strip()]
    if missing:
        log.critical("STARTUP FAIL — missing required env vars: %s", ", ".join(missing))
        sys.exit(1)


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


_check_env()

from core.invariants import InvariantViolation
from core.laws import LawViolation
from routes.chat import router as chat_router
from routes.content import router as content_router
from routes.health import router as health_router
from routes.payments import router as payments_router

app = FastAPI(title="a0replite", version="0.1.0", docs_url="/api/docs", redoc_url=None)

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
    from alembic.config import Config
    from alembic import command
    import pathlib

    alembic_ini = pathlib.Path(__file__).parent / "alembic.ini"
    if not alembic_ini.exists():
        log.warning("alembic.ini not found — skipping migrations")
        return

    loop = asyncio.get_event_loop()
    cfg = Config(str(alembic_ini))
    try:
        await loop.run_in_executor(None, lambda: command.upgrade(cfg, "head"))
        log.info("Alembic migrations applied")
    except Exception as exc:
        log.error("Alembic migration failed: %s", exc)


async def _boot_system_instance() -> None:
    from ptca import PTCAInstance
    from core.grok_adapter import call_grok_text
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

    async def grok_text_fn(model: str, messages: list) -> str:
        api_key = os.environ.get("XAI_API_KEY", "")
        return await call_grok_text(api_key, messages, model)

    from services.boot import run_boot_sequence
    try:
        await run_boot_sequence(inst, grok_text_fn, github_token)
        log.info("Boot sequence complete")
    except Exception as exc:
        log.error("Boot sequence error: %s", exc)

    app.state.system_inst = inst


async def _create_system_inst(user_id: str, db):
    from services.ptca_service import create_session
    inst, session_id = await create_session(user_id=user_id, tier="operator", db=db)
    log.info("System PTCAInstance created: %s", session_id)
    return inst, session_id

# a0replite — Replit Project

## Overview
**a0replite** is the grounded AI instance at www.interdependentway.org.
It runs a Python FastAPI backend with cryptographic state management, canonical grounding, and Grok AI chat.

## Architecture

### Backend (`backend/`)
Python 3.11 + FastAPI, served via uvicorn at port 8080.

**Core Systems:**
- **PTCA** (`core/`, `services/ptca_service.py`) — Probabilistic Tensor Context Architecture: S5 context, S6 identity, S7 memory, S8 risk, S9 audit
- **PCEA** (`core/crypto/`) — Cryptographic state sealing (AES-256-GCM) with Shamir 2-of-2 meta-key split stored as private GitHub Gists. Shares tracked in `pcea_shares` DB table.
- **EDCM** (`core/edcm/`) — Zeta normalize → morph → bone_match → span_detect → parser → turn_agg → round_agg → metrics pipeline. Canonical data from edcmbone zip (`backend/data/edcmbone_canon_data_v1.zip`).
- **ZFAE** (`core/zfae.py`) — Zero-Frame Authority Enforcement (behavioral identity inference)
- **Three-reading boot** (`services/boot.py`) — Philosophical/Operational/Technical canon readings from wayseer.github.io

**Laws:**
- Law 6: quarantine over collapse — errors are quarantined, not cascaded
- Law 8/12: capability is not authority — S4 gate checks before external effects (PUSH, MODIFY_SECRETS, SPEND_FUNDS)
- Law 9/10: all human-readable output via `core/guardian/emitter.py`
- Law 11: volatile tasks self-delete after completion with S9 audit event
- Law 14: `hmmm` invariant required on all event dicts

**Routes (`routes/`):**
- `POST /api/chat` — Grok SSE streaming chat (requires session_id, message, hmmm)
- `GET /api/chat/{session_id}/memory` — PTCA S7 memory + EDCM snapshot
- `GET /api/content` — Fetch canon content from wayseer.github.io
- `GET /api/payments/plans` — Stripe pricing plans
- `POST /api/payments/checkout` — Stripe Checkout session creation
- `POST /api/payments/webhook` — Stripe webhook handler
- `GET /guardian/snapshot` — PTCA state snapshot (operator auth required)
- `POST /guardian/approve` / `POST /guardian/revoke` — S4 approval control (operator auth required)
- `GET /guardian/audit` — S9 audit log (operator auth required)
- `GET /health` — Health check with canon/PTCA status
- `GET /` — hmmm invariant root

**Guardian Auth:**
All `/guardian/*` endpoints require `X-Operator-Key` header (first 32 hex chars of `PCEA_IKM`).

**Volatile Boot Task:**
At startup, a `website_repair` volatile task is registered and run asynchronously.
It checks the S4 PUSH gate, fetches the wayseer.github.io tree, asks Grok for a patch set,
applies patches, verifies commit SHA advancement, and records a `boot_task_complete` S9 event.
The task self-deletes after completion.

**Services:**
- `services/boot.py` — Three-reading boot sequence
- `services/ptca_service.py` — create/restore/persist PTCAInstance with full PCEA sealing
- `services/context_builder.py` — Build system prompt from PTCA memory
- `services/github.py` — GitHub file fetch and push
- `services/stripe_service.py` — Stripe payment flows
- `services/website_task.py` — Re-exports from core.boot_task (safe stub, S4-gated)

### Artifact: api-server
- **ID:** `3B4_FFSkEVBkAeYMFRJ2e`
- **Port:** 8080
- **Run:** `uvicorn backend.main:app` with `PYTHONPATH=/home/runner/workspace:/home/runner/workspace/backend`
- **Health path:** `/health`

## Required Environment Secrets

| Variable | Purpose |
|---|---|
| `XAI_API_KEY` | Grok (xAI) API key |
| `PCEA_IKM` | 64+ hex char IKM for PCEA key derivation (generate once, never regenerate) |
| `GITHUB_TOKEN_WAYSEER00` | Read wayseer.github.io + push patches + store Gist share 1 |
| `GITHUB_TOKEN_VAULT2` | Store Gist share 2 only |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `DATABASE_URL` | PostgreSQL connection string |

## Database Schema
- `chat_sessions` — PTCA session rows with all PCEA columns (nonce, aad, commitment, gist IDs)
- `pcea_shares` — Per-sentinel Gist share tracking (sentinel_id, gist_id, epoch, key_id, index)
- `chat_messages` — Chat history with EDCM snapshots including bridge matrix
- `payment_records` — Stripe payment records

## GitHub Push
To push backend to `wayseer00/a0replite`:
```bash
GITHUB_TOKEN_WAYSEER00=<token> python3 backend/scripts/push_to_github.py
```

## Python Packages
Standard: `fastapi`, `uvicorn[standard]`, `pydantic`, `httpx`, `stripe`, `asyncpg`, `sqlalchemy[asyncio]`, `alembic`, `python-dotenv`, `cryptography>=42.0`

Org libraries (from GitHub):
- `ptca-lib` — github.com/The-Interdependency/PTCA
- `guardian-state` (PCEA) — github.com/The-Interdependency/PCEA
- `edcmbone` — github.com/The-Interdependency/edcmbone (Python scaffolding; canonical data zip bundled at `backend/data/`)

See `backend/requirements.txt` for pinned versions.

## Canonical Data
`backend/data/edcmbone_canon_data_v1.zip` — validated at startup via `_meta.version`.
Contains: `bones_words_v1.json`, `bones_affixes_v1.json`, `bones_punct_v1.json`, `markers_v1.json`.
253 bone words, 35 multiword joins, 9 metrics (C/R/D/N/L/O/F/E/I), inflectional + derivational affixes.

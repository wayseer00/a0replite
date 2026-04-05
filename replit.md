# a0replite — Replit Project

## Overview
**a0replite** is the grounded AI instance at www.interdependentway.org.
It runs a Python FastAPI backend with cryptographic state management, canonical grounding, and multi-model AI orchestration.

## Architecture

### Backend (`backend/`)
Python 3.11 + FastAPI, served via uvicorn at port 8080.

**Core Systems:**
- **PTCA** (`core/`, `services/ptca_service.py`) — Probabilistic Tensor Context Architecture: S5 context, S6 identity, S7 memory, S8 risk, S9 audit
- **PCEA** (`core/crypto/`) — Cryptographic state sealing (AES-256-GCM) with Shamir 2-of-2 meta-key split stored as private GitHub Gists
- **EDCM Dual-Layer** (`core/edcm/`) — In-house Zeta parser against canonical edcmbone data + C/R/D/N/L/O/F/E/I metrics
- **ZFAE** (`core/zfae.py`) — Zero-Frame Authority Enforcement (behavioral identity inference)
- **Three-reading boot** (`services/boot_readings.py`) — Philosophical/Operational/Technical canon readings injected as system prompt

**Laws:**
- Law 6: quarantine over collapse — errors are quarantined, not cascaded
- Law 8/12: capability is not authority — gate checks before external effects
- Law 9/10: all human-readable output via `core/guardian/emitter.py`
- Law 11: volatile tasks self-delete after completion
- Law 14: `hmmm` invariant required on all event dicts

**Routes (`routes/`):**
- `/api/chat/complete` — Grok completion with three-reading system prompt
- `/api/chat/stream` — Streaming SSE
- `/api/chat/fan-out` — aimmh_lib fan_out
- `/api/chat/daisy-chain` — aimmh_lib daisy_chain
- `/api/chat/council` — aimmh_lib council
- `/api/guardian/snapshot` — PTCA state snapshot
- `/api/guardian/approve` / `/revoke` — S4 approval control
- `/api/guardian/audit` — S9 audit log
- `/api/guardian/edcm/validate` — Dual-layer EDCM evaluation
- `/api/payments/checkout` — Stripe Checkout session
- `/api/payments/intent` — Stripe PaymentIntent
- `/api/payments/webhook` — Stripe webhook handler
- `/health` — Health check

**Services:**
- `services/data_loader.py` — Loads canonical edcmbone zip from GitHub at startup
- `services/chat_service.py` — Grok adapter + aimmh orchestration
- `services/website_task.py` — Self-authorizing boot task (repair wayseer.github.io → self-delete)
- `services/stripe_service.py` — Stripe payment flows
- `services/gist_service.py` — GitHub Gist PCEA share storage

### Artifact: api-server
- **ID:** `3B4_FFSkEVBkAeYMFRJ2e`
- **Port:** 8080
- **Run:** `uvicorn backend.main:app` with `PYTHONPATH=/home/runner/workspace:/home/runner/workspace/backend`
- **Health path:** `/health`

## Required Environment Secrets

| Variable | Purpose |
|---|---|
| `XAI_API_KEY` | Grok (xAI) API key |
| `PCEA_IKM` | 32-byte hex IKM for PCEA key derivation (generate once, never regenerate) |
| `GITHUB_TOKEN_WAYSEER00` | Read wayseer.github.io + push patches + store Gist share 1 |
| `GITHUB_TOKEN_VAULT2` | Store Gist share 2 only |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |

## GitHub Push
To push backend to `wayseer00/a0replite`:
```bash
GITHUB_TOKEN_WAYSEER00=<token> python3 backend/scripts/push_to_github.py
```

## Python Packages Installed
Standard: `fastapi`, `uvicorn[standard]`, `pydantic`, `httpx`, `stripe`, `asyncpg`, `sqlalchemy[asyncio]`, `alembic`, `python-dotenv`, `cryptography>=42.0`

Org libraries (from GitHub):
- `ptca-lib` — github.com/The-Interdependency/PTCA
- `guardian-state` (PCEA) — github.com/The-Interdependency/PCEA
- `aimmh-lib` — github.com/The-Interdependency/aimmh
- `edcmbone` — github.com/The-Interdependency/edcmbone (stubs only; canonical zip fetched at startup)

## Canonical Data
`edcmbone_canon_data_v1.zip` — fetched from GitHub at startup, cached to `backend/data/`.
Contains: `bones_words_v1.json`, `bones_affixes_v1.json`, `bones_punct_v1.json`, `markers_v1.json`.

from __future__ import annotations

import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.edcm.bone_match import match_bones
from core.edcm.data_loader import get_canon
from core.edcm.metrics import BehavioralVector, compute_behavioral_vector, compute_bridge
from core.edcm.morph import segment
from core.edcm.normalize import normalize
from core.edcm.parser import parse_utterances
from core.edcm.round_agg import aggregate_round
from core.edcm.span_detect import detect_spans
from core.edcm.turn_agg import aggregate_turn, OperatorVector
from core.guardian import audit
from core.guardian.emitter import emit
from core.guardian.recovery import quarantine
from core.grok_adapter import stream_grok
from core.invariants import require_hmmm
from models.message import ChatPayload
from models.session import MemoryResponse
from services.context_builder import build_system_prompt
from services.ptca_service import create_session, persist_session, restore_session

router = APIRouter(prefix="/api", tags=["chat"])

_DEFAULT_MODEL = "grok-3"


def _get_db(request: Request):
    return request.app.state.db


@router.post("/chat")
async def chat(payload: ChatPayload, request: Request) -> StreamingResponse:
    require_hmmm(payload.model_dump(), "POST /api/chat")
    db = _get_db(request)

    try:
        inst = await restore_session(payload.session_id, db)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    canon = get_canon()
    normalized, tokens = normalize(payload.message, canon)
    all_bone_tokens = []
    for t in tokens:
        segs = segment(t, canon)
        all_bone_tokens.extend(match_bones(segs, canon))

    turn_id = f"t{int(time.time()*1000)}"
    marker_hits = detect_spans(normalized, canon, turn_id)
    user_op_vec = aggregate_turn(all_bone_tokens)

    edcm_snapshot = user_op_vec.as_dict()

    edcm_from_session = inst.recall("last_edcm_snapshot", default=None)
    system_prompt = build_system_prompt(inst, edcm_from_session)

    api_key = _xai_key()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.message},
    ]

    first_interaction_events = audit.get_events(inst, "first_interaction_complete")
    is_first = len(first_interaction_events) == 0
    guardrails_prefix = ""
    if is_first:
        guardrails = inst.recall("iw_guardrails", default=None)
        if guardrails:
            guardrails_prefix = f"{guardrails}\n\n---\n\n"

    async def event_stream() -> AsyncGenerator[bytes, None]:
        guardrails_sent = False
        pending: list[str] = []

        def _emit_to_buffer(text: str) -> None:
            pending.append(text)

        if guardrails_prefix:
            for line in guardrails_prefix.split("\n"):
                if line:
                    emit(inst, line, _emit_to_buffer)
                    while pending:
                        token = pending.pop(0)
                        yield f"data: {token}\n\n".encode()
            guardrails_sent = True

        if is_first:
            audit.append_event(
                inst, "first_interaction_complete",
                {"hmmm": "", "session_id": payload.session_id, "guardrails_sent": guardrails_sent}
            )

        full_response = ""
        async for chunk in stream_grok(api_key, messages, _DEFAULT_MODEL):
            full_response += chunk
            emit(inst, chunk, _emit_to_buffer)
            while pending:
                token = pending.pop(0)
                yield f"data: {token}\n\n".encode()

        yield b"data: [DONE]\n\n"

        try:
            utterances = [
                {"actor_id": "user", "raw_text": payload.message, "timestamp": time.time()},
                {"actor_id": "a0replite", "raw_text": full_response, "timestamp": time.time()},
            ]
            conversation = parse_utterances(utterances)
            round_aggs = aggregate_round(
                marker_hits, total_turns=len(conversation.turns), total_tokens=len(tokens)
            )

            response_normalized, response_tokens = normalize(full_response, canon)
            response_bone_tokens = []
            for t in response_tokens:
                segs = segment(t, canon)
                response_bone_tokens.extend(match_bones(segs, canon))
            response_op_vec = aggregate_turn(response_bone_tokens)

            behavioral_vec = compute_behavioral_vector(round_aggs, [user_op_vec, response_op_vec], canon)

            raw_op_history: list[dict] = inst.recall("_op_history", default=[])
            raw_bv_history: list[dict] = inst.recall("_bv_history", default=[])
            op_history: list[OperatorVector] = [
                OperatorVector.from_dict(d) if isinstance(d, dict) else d
                for d in raw_op_history
            ]
            bv_history: list[BehavioralVector] = [
                BehavioralVector.from_dict(d) if isinstance(d, dict) else d
                for d in raw_bv_history
            ]
            op_history = (op_history + [user_op_vec])[-20:]
            bv_history = (bv_history + [behavioral_vec])[-20:]
            bridge = compute_bridge(op_history, bv_history)

            inst.remember("last_edcm_snapshot", behavioral_vec.as_dict())
            inst.remember("last_bridge_matrix", bridge.as_dict())
            inst.remember("_op_history", [ov.as_dict() for ov in op_history])
            inst.remember("_bv_history", [bv.as_dict() for bv in bv_history])
            inst.push_context({"key": "last_message_turn_id", "val": turn_id})

            full_assistant_snapshot = {**behavioral_vec.as_dict(), "bridge": bridge.as_dict()}

            await db.execute(
                """
                INSERT INTO chat_messages
                  (message_id, session_id, role, content, turn_id, edcm_snapshot)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                str(uuid.uuid4()), payload.session_id, "user", payload.message, turn_id,
                json.dumps(edcm_snapshot),
            )
            await db.execute(
                """
                INSERT INTO chat_messages
                  (message_id, session_id, role, content, turn_id, edcm_snapshot)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                str(uuid.uuid4()), payload.session_id, "assistant", full_response, turn_id,
                json.dumps(full_assistant_snapshot),
            )
            await persist_session(payload.session_id, inst, db)
        except Exception as exc:
            quarantine(exc, "chat:post_stream", inst)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/chat/{session_id}/memory", response_model=MemoryResponse)
async def get_memory(session_id: str, request: Request) -> MemoryResponse:
    db = _get_db(request)
    try:
        inst = await restore_session(session_id, db)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    row = await db.fetchrow(
        "SELECT tier, pcea_epoch FROM chat_sessions WHERE session_id=$1", session_id
    )
    tier = row["tier"] if row else "seeker"
    epoch = row["pcea_epoch"] if row else 0
    memory = inst.snapshot().get("S7_MEMORY", {}).get("store", {})
    s8_risk = inst.snapshot().get("S8_RISK", {}).get("score", 0.0)
    edcm_last = inst.recall("last_edcm_snapshot", default=None)

    return MemoryResponse(
        s7_key_count=len(memory),
        s8_risk=s8_risk,
        tier=tier,
        pcea_epoch=epoch,
        edcm_last=edcm_last,
        hmmm="",
    )


def _xai_key() -> str:
    import os
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="XAI_API_KEY not configured")
    return key

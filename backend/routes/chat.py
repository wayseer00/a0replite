from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.invariants import InvariantViolation, require_hmmm
from models.chat import (
    ChatRequest,
    ChatResponse,
    CouncilRequest,
    CouncilResponse,
    DaisyChainRequest,
    DaisyChainResponse,
    FanOutRequest,
    FanOutResponse,
)
from services.chat_service import (
    chat_complete,
    run_aimmh_council,
    run_aimmh_daisy_chain,
    run_aimmh_fan_out,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/complete", response_model=ChatResponse)
async def complete(req: ChatRequest) -> ChatResponse:
    require_hmmm(req.model_dump(), "POST /chat/complete")
    msgs = [m.model_dump() for m in req.messages]
    result = await chat_complete(msgs, model=req.model, stream=False)
    return ChatResponse(content=str(result), model=req.model, hmmm=req.hmmm)


@router.post("/stream")
async def stream(req: ChatRequest) -> StreamingResponse:
    require_hmmm(req.model_dump(), "POST /chat/stream")
    msgs = [m.model_dump() for m in req.messages]
    gen: AsyncGenerator[str, None] = await chat_complete(msgs, model=req.model, stream=True)

    async def event_stream() -> AsyncGenerator[bytes, None]:
        async for chunk in gen:
            yield f"data: {json.dumps({'content': chunk})}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/fan-out", response_model=FanOutResponse)
async def fan_out(req: FanOutRequest) -> FanOutResponse:
    require_hmmm(req.model_dump(), "POST /chat/fan-out")
    msgs = [m.model_dump() for m in req.messages]
    results = await run_aimmh_fan_out(msgs, model=req.model, n=req.n)
    return FanOutResponse(results=results, hmmm=req.hmmm)


@router.post("/daisy-chain", response_model=DaisyChainResponse)
async def daisy_chain(req: DaisyChainRequest) -> DaisyChainResponse:
    require_hmmm(req.model_dump(), "POST /chat/daisy-chain")
    steps = [s.model_dump() for s in req.steps]
    result = await run_aimmh_daisy_chain(steps, model=req.model)
    return DaisyChainResponse(result=result, hmmm=req.hmmm)


@router.post("/council", response_model=CouncilResponse)
async def council(req: CouncilRequest) -> CouncilResponse:
    require_hmmm(req.model_dump(), "POST /chat/council")
    responses = await run_aimmh_council(req.question, req.roles, model=req.model)
    return CouncilResponse(responses=responses, hmmm=req.hmmm)

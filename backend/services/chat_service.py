from __future__ import annotations

import os
import time
from typing import Any, AsyncGenerator, Optional

from core.grok_adapter import make_grok_call_fn, stream_grok
from core.invariants import require_hmmm
from services.boot_readings import build_system_prompt
from services.data_loader import get_parser


async def chat_complete(
    messages: list[dict],
    model: str = "grok-3",
    stream: bool = False,
) -> str | AsyncGenerator[str, None]:
    """Send messages to Grok, prepending the three-reading system prompt."""
    api_key = _api_key()
    parser = get_parser()
    system_prompt = build_system_prompt(parser)

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    if stream:
        return stream_grok(api_key, full_messages, model)
    call_fn = make_grok_call_fn(api_key, model)
    return await call_fn(model, full_messages)


def _api_key() -> str:
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        raise RuntimeError("XAI_API_KEY not set — cannot make Grok API calls")
    return key


async def run_aimmh_fan_out(
    messages: list[dict],
    model: str = "grok-3",
    n: int = 3,
) -> list[str]:
    """Run fan_out: send same messages to N parallel Grok calls."""
    from aimmh_lib import fan_out
    api_key = _api_key()
    call_fn = make_grok_call_fn(api_key, model)
    results = await fan_out(call_fn, model, messages, n=n)
    return results


async def run_aimmh_daisy_chain(
    steps: list[dict],
    model: str = "grok-3",
) -> str:
    """Run daisy_chain: pipe output of step N into input of step N+1."""
    from aimmh_lib import daisy_chain
    api_key = _api_key()
    call_fn = make_grok_call_fn(api_key, model)
    result = await daisy_chain(call_fn, model, steps)
    return result


async def run_aimmh_council(
    question: str,
    roles: list[str],
    model: str = "grok-3",
) -> list[dict]:
    """Run council: each role responds to the same question."""
    from aimmh_lib import council
    api_key = _api_key()
    call_fn = make_grok_call_fn(api_key, model)
    responses = await council(call_fn, model, question, roles=roles)
    return responses

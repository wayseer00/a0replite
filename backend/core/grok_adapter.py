from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

_XAI_BASE = "https://api.x.ai/v1"
_TIMEOUT = 120.0


def make_grok_call_fn(api_key: str, model: str = "grok-3"):
    """Return a CallFn compatible with aimmh_lib's interface: async (model_id, messages) -> str."""
    async def call_fn(model_id: str, messages: list[dict]) -> str:
        target = model_id or model
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_XAI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": target, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    return call_fn


async def stream_grok(
    api_key: str,
    messages: list[dict],
    model: str = "grok-3",
) -> AsyncGenerator[str, None]:
    """Stream Grok tokens as an async generator of text chunks."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        async with client.stream(
            "POST",
            f"{_XAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

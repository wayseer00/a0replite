from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

_XAI_BASE = "https://api.x.ai/v1"
_TIMEOUT = 120.0


def _record_grok(ok: bool) -> None:
    try:
        from core import status_registry
        if ok:
            status_registry.record_ok("grok")
        else:
            status_registry.record_unavailable("grok")
    except Exception:
        pass


def make_grok_call_fn(api_key: str, model: str = "grok-3"):
    """Return a CallFn compatible with aimmh_lib's interface: async (model_id, messages) -> str."""
    async def call_fn(model_id: str, messages: list[dict]) -> str:
        target = model_id or model
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{_XAI_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": target, "messages": messages, "stream": False},
                )
                resp.raise_for_status()
                result = resp.json()["choices"][0]["message"]["content"]
                _record_grok(True)
                return result
            except Exception:
                _record_grok(False)
                raise
    return call_fn


async def call_grok_text(api_key: str, messages: list[dict], model: str = "grok-3") -> str:
    """Non-streaming Grok call — returns full response text."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{_XAI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            _record_grok(True)
            return result
        except Exception:
            _record_grok(False)
            raise


async def stream_grok(
    api_key: str,
    messages: list[dict],
    model: str = "grok-3",
) -> AsyncGenerator[str, None]:
    """Stream Grok tokens as an async generator of text chunks."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            async with client.stream(
                "POST",
                f"{_XAI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                _record_grok(True)
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
        except Exception:
            _record_grok(False)
            raise

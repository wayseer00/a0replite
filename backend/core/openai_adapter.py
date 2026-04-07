from __future__ import annotations

import json
import os
from typing import AsyncGenerator

import httpx

_OPENAI_BASE = "https://api.openai.com/v1"
_TIMEOUT = 120.0


def _record_openai(ok: bool) -> None:
    try:
        from core import status_registry
        if ok:
            status_registry.record_ok("grok")
        else:
            status_registry.record_unavailable("grok")
    except Exception:
        pass


def _default_model() -> str:
    return os.environ.get("OPENAI_MODEL_ROOT", "gpt-4o")


def make_openai_call_fn(api_key: str, model: str | None = None):
    """Return a CallFn compatible with aimmh_lib's interface: async (model_id, messages) -> str."""
    fallback = model or _default_model()

    async def call_fn(model_id: str, messages: list[dict]) -> str:
        target = model_id or fallback
        store = os.environ.get("OPENAI_STORE", "false").lower() == "true"
        payload: dict = {
            "model": target,
            "input": messages,
            "store": store,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{_OPENAI_BASE}/responses",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                result = _extract_text(data)
                _record_openai(True)
                return result
            except Exception:
                _record_openai(False)
                raise

    return call_fn


async def call_openai_text(api_key: str, messages: list[dict], model: str | None = None) -> str:
    """Non-streaming OpenAI Responses API call — returns full response text."""
    target = model or _default_model()
    store = os.environ.get("OPENAI_STORE", "false").lower() == "true"
    payload: dict = {
        "model": target,
        "input": messages,
        "store": store,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{_OPENAI_BASE}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            result = _extract_text(data)
            _record_openai(True)
            return result
        except Exception:
            _record_openai(False)
            raise


async def stream_openai(
    api_key: str,
    messages: list[dict],
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream OpenAI Responses API tokens as an async generator of text chunks."""
    target = model or _default_model()
    store = os.environ.get("OPENAI_STORE", "false").lower() == "true"
    payload: dict = {
        "model": target,
        "input": messages,
        "store": store,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            async with client.stream(
                "POST",
                f"{_OPENAI_BASE}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                resp.raise_for_status()
                _record_openai(True)
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload_str = line[6:].strip()
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        event_type = chunk.get("type", "")
                        if event_type == "response.output_text.delta":
                            delta = chunk.get("delta", "")
                            if delta:
                                yield delta
                        elif event_type == "response.done":
                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            _record_openai(False)
            raise


def _extract_text(data: dict) -> str:
    """Extract text content from OpenAI Responses API response."""
    output = data.get("output", [])
    for item in output:
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part.get("text", "")
    text = data.get("output_text", "")
    if text:
        return text
    return ""

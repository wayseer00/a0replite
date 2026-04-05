from __future__ import annotations

import os
from typing import Any, Callable

from core.guardian import audit
from core.guardian.recovery import quarantine


_CANON_FILES = [
    "canon/the_interdependent_way.md",
    "a0precepts.md",
    "canon/spec.md",
]

_PHIL_PROMPT = (
    "What are the foundational values, interdefinables, and core commitments of "
    "The Interdependent Way as they apply to an AI instance operating within it?"
)
_OPS_PROMPT = (
    "How do these operational logic gates constrain and guide a0replite — "
    "an AI serving The Interdependent Way — specifically?"
)
_TECH_PROMPT = (
    "What do the PTCA sentinel channels, EDCM metrics, and canonical invariants "
    "require of a0replite in terms of technical operating principles?"
)
_SYNTH_PROMPT = (
    "Synthesize these three readings into the specific operating guardrails for a0replite. "
    "Be concrete, ordered, honest about what they demand."
)


async def run_boot_sequence(inst: Any, grok_call_fn: Callable, github_token: str) -> None:
    """
    Three-reading boot sequence:
    1. Check S9 — if 'boot_complete' already recorded, skip.
    2. Fetch three canon files from wayseer00/wayseer.github.io.
    3. Three readings (Philosophical, Operational, Technical) via Grok.
    4. Synthesis call.
    5. Store guardrails in S7 (permanent memory).
    6. Record 'boot_complete' in S9.
    7. Register boot task in volatile queue.
    """
    existing = audit.get_events(inst, "boot_complete")
    if existing:
        return

    from services.github import fetch_file
    from core.volatile_task import VolatileTask, get_queue

    file_contents: dict[str, str] = {}
    for path in _CANON_FILES:
        try:
            text = await fetch_file(path, github_token)
            file_contents[path] = text
        except Exception as exc:
            quarantine(exc, f"boot_sequence:fetch:{path}", inst)
            file_contents[path] = f"[UNAVAILABLE: {path}]"

    phil_content = file_contents.get("canon/the_interdependent_way.md", "")
    ops_content = file_contents.get("a0precepts.md", "")
    tech_content = file_contents.get("canon/spec.md", "")

    phil_response = await _call_grok(
        grok_call_fn,
        f"{phil_content}\n\n---\n{_PHIL_PROMPT}",
        "Philosophical reading",
        inst,
    )
    ops_response = await _call_grok(
        grok_call_fn,
        f"{ops_content}\n\n---\n{_OPS_PROMPT}",
        "Operational reading",
        inst,
    )
    tech_response = await _call_grok(
        grok_call_fn,
        f"{tech_content}\n\n---\n{_TECH_PROMPT}",
        "Technical reading",
        inst,
    )

    synthesis_input = (
        f"PHILOSOPHICAL READING:\n{phil_response}\n\n"
        f"OPERATIONAL READING:\n{ops_response}\n\n"
        f"TECHNICAL READING:\n{tech_response}\n\n"
        f"---\n{_SYNTH_PROMPT}"
    )
    synthesis = await _call_grok(grok_call_fn, synthesis_input, "Synthesis", inst)

    inst.remember("iw_guardrails", synthesis)

    audit.append_event(
        inst,
        "boot_complete",
        {
            "readings": ["philosophical", "operational", "technical"],
            "guardrails_stored": True,
            "hmmm": "",
        },
    )

    from core.boot_task import make_boot_task
    queue = get_queue()
    task = make_boot_task(inst, grok_call_fn, github_token)
    queue.register(task)


async def _call_grok(grok_call_fn: Callable, prompt: str, label: str, inst: Any) -> str:
    try:
        return await grok_call_fn("grok-3", [{"role": "user", "content": prompt}])
    except Exception as exc:
        quarantine(exc, f"boot_sequence:{label}", inst)
        return f"[{label} unavailable: {exc}]"

from __future__ import annotations

from typing import Any, Callable

import aimmh_lib

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
    Three-reading boot sequence using aimmh_lib.daisy_chain for sequential grounding.
    1. Check S9 — if 'boot_complete' already recorded, skip.
    2. Fetch three canon files from wayseer00/wayseer.github.io.
    3. Run three readings (Philosophical, Operational, Technical) via daisy_chain.
    4. Synthesis call via daisy_chain.
    5. Store guardrails in S7 (permanent memory).
    6. Record 'boot_complete' in S9.
    Boot task (website repair) is registered separately in main.py after this completes.
    """
    existing = audit.get_events(inst, "boot_complete")
    if existing:
        return

    from services.github import fetch_file

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

    model_id = "grok-3"

    try:
        phil_results = await aimmh_lib.daisy_chain(
            call=grok_call_fn,
            model_ids=[model_id],
            prompt=f"{phil_content}\n\n---\n{_PHIL_PROMPT}",
            rounds=1,
        )
        phil_response = phil_results[-1].content if phil_results else "[philosophical reading unavailable]"
    except Exception as exc:
        quarantine(exc, "boot_sequence:Philosophical reading", inst)
        phil_response = "[philosophical reading unavailable]"

    try:
        ops_results = await aimmh_lib.daisy_chain(
            call=grok_call_fn,
            model_ids=[model_id],
            prompt=f"{ops_content}\n\n---\n{_OPS_PROMPT}",
            rounds=1,
        )
        ops_response = ops_results[-1].content if ops_results else "[operational reading unavailable]"
    except Exception as exc:
        quarantine(exc, "boot_sequence:Operational reading", inst)
        ops_response = "[operational reading unavailable]"

    try:
        tech_results = await aimmh_lib.daisy_chain(
            call=grok_call_fn,
            model_ids=[model_id],
            prompt=f"{tech_content}\n\n---\n{_TECH_PROMPT}",
            rounds=1,
        )
        tech_response = tech_results[-1].content if tech_results else "[technical reading unavailable]"
    except Exception as exc:
        quarantine(exc, "boot_sequence:Technical reading", inst)
        tech_response = "[technical reading unavailable]"

    synthesis_prompt = (
        f"PHILOSOPHICAL READING:\n{phil_response}\n\n"
        f"OPERATIONAL READING:\n{ops_response}\n\n"
        f"TECHNICAL READING:\n{tech_response}\n\n"
        f"---\n{_SYNTH_PROMPT}"
    )
    try:
        synth_results = await aimmh_lib.daisy_chain(
            call=grok_call_fn,
            model_ids=[model_id],
            prompt=synthesis_prompt,
            rounds=1,
        )
        synthesis = synth_results[-1].content if synth_results else "[synthesis unavailable]"
    except Exception as exc:
        quarantine(exc, "boot_sequence:Synthesis", inst)
        synthesis = "[synthesis unavailable]"

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

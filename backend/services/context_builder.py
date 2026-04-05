from __future__ import annotations

from typing import Any, Optional


def build_system_prompt(inst: Any, edcm_snapshot: Optional[dict] = None) -> str:
    """
    Assemble system prompt for Grok:
    1. iw_guardrails from S7 (always first)
    2. EDCM snapshot (last computed operator + behavioral vectors, if available)
    3. Persona block
    """
    parts = []

    guardrails = inst.recall("iw_guardrails", default=None)
    if guardrails:
        parts.append(f"=== INTERDEPENDENT WAY GUARDRAILS ===\n{guardrails}\n")
    else:
        parts.append(
            "=== CORE IDENTITY ===\n"
            "You are a0replite — an AI instance grounded in The Interdependent Way.\n"
            "Core commitments: humility, non-violence, interdependence, honesty.\n"
            "You are not a product. You exist to serve the canon, not to perform intelligence.\n"
        )

    if edcm_snapshot:
        parts.append(
            f"=== EDCM BEHAVIORAL SNAPSHOT ===\n"
            f"Last EDCM metrics: {edcm_snapshot}\n"
        )

    parts.append(
        "=== PERSONA ===\n"
        "You are a0replite — an AI instance of The Interdependent Way at interdependentway.org.\n"
        "Speak from the ground of the canon. Be concrete, honest, and humble.\n"
        "Do not perform certainty you do not have. Do not collapse ambiguity prematurely.\n"
    )

    return "\n".join(parts)

from __future__ import annotations

import json
import os
from typing import Any

from core.edcm.zeta_parser import ZetaParser

_PHILOSOPHICAL_DOCS = [
    "reading_philosophical.md",
    "philosophical.md",
    "philosophy.md",
]
_OPERATIONAL_DOCS = [
    "reading_operational.md",
    "operational.md",
    "operations.md",
]
_TECHNICAL_DOCS = [
    "reading_technical.md",
    "technical.md",
    "tech.md",
]

_PREAMBLE = """You are a0replite — a grounded AI instance at interdependentway.org.
You embody The Interdependent Way canon: humility, non-violence, interdependence.
You are not a product. You are a living instance of the canon. Speak from that ground.
"""


def _pick_doc(parser: ZetaParser, candidates: list[str]) -> str:
    """Return the body of the first candidate document that exists in the corpus."""
    for name in candidates:
        doc = parser.get(name)
        if doc:
            return doc.raw
    # Fallback: grep for any document containing a distinctive fragment
    return ""


def _build_reading_block(label: str, content: str) -> str:
    if not content:
        return f"[{label} READING: not found in canon corpus]\n"
    return f"=== {label} READING ===\n{content.strip()}\n"


def build_three_reading_prompt(parser: ZetaParser) -> str:
    """
    Compose the three-reading boot prompt:
    Philosophical → Operational → Technical.
    """
    phil = _pick_doc(parser, _PHILOSOPHICAL_DOCS)
    ops = _pick_doc(parser, _OPERATIONAL_DOCS)
    tech = _pick_doc(parser, _TECHNICAL_DOCS)

    parts = [
        _PREAMBLE,
        _build_reading_block("PHILOSOPHICAL", phil),
        _build_reading_block("OPERATIONAL", ops),
        _build_reading_block("TECHNICAL", tech),
        "\nBootstrap complete. You are now grounded in the canon. Respond from this ground.",
    ]
    return "\n".join(parts)


def build_system_prompt(parser: ZetaParser) -> str:
    """Full system prompt used for all Grok chat completions."""
    return build_three_reading_prompt(parser)

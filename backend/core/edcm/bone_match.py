from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.edcm.data_loader import CanonicalData

_PRIORITY = {"P": 0, "K": 1, "Q": 2, "T": 3, "S": 4}


@dataclass
class BoneToken:
    token: str
    family: str
    source: str


def _priority_family(families: list[str]) -> str:
    """Apply collision priority P>K>Q>T>S."""
    if not families:
        return "S"
    return min(families, key=lambda f: _PRIORITY.get(f, 99))


def match_bones(tokens: list[str], canon: CanonicalData) -> list[BoneToken]:
    """
    Match tokens (including affixes from morph) to PKQTS bone families.
    Applies collision priority P>K>Q>T>S for multi-family tokens.
    Flesh tokens (no match) are silently ignored.
    """
    result: list[BoneToken] = []

    for token in tokens:
        t = token.lower()

        if t in canon.word_to_primary:
            families = canon.word_to_families.get(t, [canon.word_to_primary[t]])
            family = _priority_family(families)
            result.append(BoneToken(token=token, family=family, source="word"))
            continue

        if t in canon.punct_rules:
            result.append(BoneToken(token=token, family=canon.punct_rules[t], source="punct"))
            continue

    return result

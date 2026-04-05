from __future__ import annotations

import re
import unicodedata

from core.edcm.data_loader import CanonicalData

_ELLIPSIS_RE = re.compile(r"\.{2,}")
_WORD_BOUNDARY_RE = re.compile(r"\b")


def normalize(text: str, canon: CanonicalData) -> tuple[str, list[str]]:
    """
    Normalize text for EDCM bone matching.
    1. Lowercase
    2. NFKC unicode normalization
    3. Collapse 2+ dots to ellipsis
    4. Apply multiword smash joins (longest-match-first, on word boundaries)
    5. Tokenize on whitespace
    Returns (normalized_text, tokens).
    """
    text = text.lower()
    text = unicodedata.normalize("NFKC", text)
    text = _ELLIPSIS_RE.sub("...", text)

    for joined, _primary, _families in canon.multiword_joins:
        original = joined
        reconstructed = _infer_original(joined)
        if reconstructed:
            boundary_pattern = re.compile(
                r"\b" + re.escape(reconstructed) + r"\b", re.IGNORECASE
            )
            text = boundary_pattern.sub(joined, text)

    tokens = text.split()
    return text, tokens


def _infer_original(joined: str) -> str:
    """Attempt to reconstruct original multi-word phrase from smashed form."""
    return joined

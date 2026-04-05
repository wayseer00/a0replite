from __future__ import annotations

import re
import unicodedata

from core.edcm.data_loader import CanonicalData

_ELLIPSIS_RE = re.compile(r"\.{2,}")


def normalize(text: str, canon: CanonicalData) -> tuple[str, list[str]]:
    """
    Normalize text for EDCM bone matching.
    1. Lowercase
    2. NFKC unicode normalization
    3. Collapse 2+ dots to ellipsis
    4. Apply multiword smash joins (longest-match-first on original phrase → joined form)
    5. Tokenize on whitespace
    Returns (normalized_text, tokens).
    """
    text = text.lower()
    text = unicodedata.normalize("NFKC", text)
    text = _ELLIPSIS_RE.sub("...", text)

    for joined, original, _primary, _families in canon.multiword_joins:
        if not original:
            continue
        pattern = re.compile(r"\b" + re.escape(original) + r"\b")
        text = pattern.sub(joined, text)

    tokens = text.split()
    return text, tokens

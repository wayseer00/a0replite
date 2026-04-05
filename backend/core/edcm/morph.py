from __future__ import annotations

from core.edcm.data_loader import CanonicalData

_VOWELS = frozenset("aeiou")
_CONSONANT_RE_CHARS = "bcdfghjklmnpqrstvwxyz"


def _has_vowel(s: str) -> bool:
    return any(c in _VOWELS for c in s)


def segment(token: str, canon: CanonicalData) -> list[str]:
    """
    Affix segmentation. Returns [stem_token, *affix_tokens].
    Affixes that produce bone tokens are returned as separate tokens.
    """
    result = [token]
    remaining = token

    for prefix_entry in canon.derivational_prefixes:
        affix = prefix_entry.get("affix", "")
        if not affix:
            continue
        if remaining.startswith(affix) and len(remaining) > len(affix):
            stem = remaining[len(affix):]
            if _has_vowel(stem) and len(stem) >= 2:
                result = [stem, affix]
                remaining = stem
                break

    for suffix_entry in canon.derivational_suffixes:
        affix = suffix_entry.get("affix", "")
        if not affix:
            continue
        if remaining.endswith(affix) and len(remaining) > len(affix):
            stem = remaining[: -len(affix)]
            if _has_vowel(stem) and len(stem) >= 2:
                if len(result) == 1:
                    result = [stem, affix]
                else:
                    result[-1] = stem
                    result.append(affix)
                remaining = stem
                break

    for infl_entry in canon.inflectional_affixes:
        affix = infl_entry.get("affix", "")
        if not affix:
            continue
        a_type = infl_entry.get("type", "suffix")
        if a_type == "suffix" and remaining.endswith(affix) and len(remaining) > len(affix):
            stem = remaining[: -len(affix)]
            if _has_vowel(stem) and len(stem) >= 2:
                if affix not in result:
                    result.append(affix)
                break

    return result

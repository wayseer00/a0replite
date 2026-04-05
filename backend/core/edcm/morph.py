from __future__ import annotations

from core.edcm.data_loader import CanonicalData

_VOWELS = frozenset("aeiou")

# Families that accept -s/-es as productive pluralization (noun) or
# third-person singular (verb).  All content-word bone families qualify.
_NOUN_VERB_FAMILIES = frozenset({"P", "K", "Q", "T", "S"})

# Raw affix strings (with hyphens) that represent the nominal/verbal -s suffix.
_S_INFLECTIONS = frozenset({"-s", "-es", "-'s"})


def _has_vowel(s: str) -> bool:
    return any(c in _VOWELS for c in s)


def _bare_affix(affix: str) -> str:
    """Strip leading/trailing hyphens from affix notation (NOT apostrophes)."""
    return affix.lstrip("-").rstrip("-")


def segment(token: str, canon: CanonicalData) -> list[str]:
    """
    Affix segmentation per EDCM spec.
    1. Try derivational prefixes (longest first). Accept if stem has vowel, len>=2,
       and stem is in canon.word_to_primary OR has vowel heuristic.
    2. Try derivational suffixes on the resulting stem.
    3. Try inflectional suffixes (-s, -es, -'s) on the final stem.
       For -s specifically: accept if stem is in canon OR stem+vowel heuristic holds.
    Returns [stem, *affixes] where each affix that produced a match is included.
    """
    result = [token]
    remaining = token.lower()

    for prefix_entry in canon.derivational_prefixes:
        raw_affix = prefix_entry.get("affix", "")
        affix = _bare_affix(raw_affix)
        if not affix:
            continue
        if remaining.startswith(affix) and len(remaining) > len(affix):
            stem = remaining[len(affix):]
            if _has_vowel(stem) and len(stem) >= 2 and (stem in canon.word_to_primary or _has_vowel(stem)):
                result = [stem, affix]
                remaining = stem
                break

    for suffix_entry in canon.derivational_suffixes:
        raw_affix = suffix_entry.get("affix", "")
        affix = _bare_affix(raw_affix)
        if not affix:
            continue
        if remaining.endswith(affix) and len(remaining) > len(affix):
            stem = remaining[: -len(affix)]
            if _has_vowel(stem) and len(stem) >= 2 and (stem in canon.word_to_primary or _has_vowel(stem)):
                if len(result) == 1:
                    result = [stem, affix]
                else:
                    result[0] = stem
                    result.append(affix)
                remaining = stem
                break

    for infl_entry in canon.inflectional_affixes:
        raw_affix = infl_entry.get("affix", "")
        affix_type = infl_entry.get("type", "suffix")
        affix = _bare_affix(raw_affix)
        if not affix or affix_type != "suffix":
            continue
        if remaining.endswith(affix) and len(remaining) > len(affix):
            stem = remaining[: -len(affix)]
            if raw_affix in _S_INFLECTIONS:
                # Noun/verb disambiguation for -s/-es/-'s:
                # 1. If stem is a recognized canon word, accept only if its
                #    primary bone family is a content-word family (noun or verb).
                # 2. If stem is unknown, apply general vowel heuristic.
                if stem in canon.word_to_primary:
                    accept = canon.word_to_primary[stem] in _NOUN_VERB_FAMILIES
                else:
                    accept = _has_vowel(stem) and len(stem) >= 2
            else:
                accept = _has_vowel(stem) and len(stem) >= 2
            if accept:
                if affix not in result:
                    result.append(affix)
                break

    return result

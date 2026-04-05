from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ZIP_PATH = Path(__file__).parent.parent.parent / "data" / "edcmbone_canon_data_v1.zip"


class CanonLoadError(Exception):
    """Raised when canonical data fails validation at startup."""


@dataclass(frozen=True)
class CanonicalData:
    word_to_primary: dict[str, str]
    word_to_families: dict[str, list[str]]
    multiword_joins: list[tuple[str, str, str, list[str]]]
    inflectional_affixes: list[dict]
    derivational_prefixes: list[dict]
    derivational_suffixes: list[dict]
    punct_rules: dict[str, str]
    markers_by_metric: dict[str, dict]
    versions: dict[str, str]


def _load_json_from_zip(zf: zipfile.ZipFile, name: str) -> dict:
    names = zf.namelist()
    candidates = [n for n in names if n == name or n.endswith(f"/{name}")]
    if not candidates:
        raise CanonLoadError(f"File {name!r} not found in canonical zip")
    return json.loads(zf.read(candidates[0]))


def _validate_meta(data: dict, filename: str) -> str:
    meta = data.get("_meta")
    if not isinstance(meta, dict):
        raise CanonLoadError(f"{filename}: missing _meta dict")
    version = meta.get("version")
    if not version:
        raise CanonLoadError(f"{filename}: _meta.version missing")
    return str(version)


def _build_word_lookups(
    words_data: dict,
) -> tuple[dict[str, str], dict[str, list[str]], list[tuple[str, str, str, list[str]]]]:
    word_to_primary: dict[str, str] = {}
    word_to_families: dict[str, list[str]] = {}

    for entry in words_data.get("words", []):
        w = entry.get("word", "").lower()
        if not w:
            continue
        word_to_primary[w] = entry.get("primary", "S")
        word_to_families[w] = entry.get("families", [entry.get("primary", "S")])

    joins: list[tuple[str, str, str, list[str]]] = []
    for entry in words_data.get("multiword_joins", []):
        joined = entry.get("joined", "").lower()
        original = entry.get("original", "").lower()
        if not joined or not original:
            continue
        joins.append((joined, original, entry.get("primary", "S"), entry.get("families", [])))
    joins.sort(key=lambda t: len(t[1]), reverse=True)
    return word_to_primary, word_to_families, joins


def _build_affix_lookups(
    affixes_data: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    infl = affixes_data.get("inflectional", {}).get("affixes", [])
    dp = affixes_data.get("derivational_prefixes", {}).get("affixes", [])
    ds = affixes_data.get("derivational_suffixes", {}).get("affixes", [])
    infl_sorted = sorted(infl, key=lambda a: len(a.get("affix", "").lstrip("-").rstrip("-")), reverse=True)
    dp_sorted = sorted(dp, key=lambda a: len(a.get("affix", "").lstrip("-").rstrip("-")), reverse=True)
    ds_sorted = sorted(ds, key=lambda a: len(a.get("affix", "").lstrip("-").rstrip("-")), reverse=True)
    return infl_sorted, dp_sorted, ds_sorted


def _build_punct_rules(punct_data: dict) -> dict[str, str]:
    rules: dict[str, str] = {}
    punct = punct_data.get("punctuation", [])
    if isinstance(punct, list):
        entries = punct
    elif isinstance(punct, dict):
        entries = punct.get("rules", [])
    else:
        entries = []
    for entry in entries:
        mark = entry.get("mark") or entry.get("symbol", "")
        if mark:
            rules[mark] = entry.get("primary", "S")
    return rules


def _build_markers(markers_data: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for metric_id in ("C", "R", "D", "N", "L", "O", "F", "E", "I"):
        if metric_id not in markers_data:
            continue
        section = markers_data[metric_id]
        out[metric_id] = {
            "formula": section.get("formula", ""),
            "requires_embeddings": section.get("requires_embeddings", False),
            "computable_from_markers": section.get("computable_from_markers", True),
            "explanation": section.get("explanation", ""),
            "marker_lists": {
                k: v
                for k, v in section.get("markers", {}).items()
                if isinstance(v, list)
            },
        }
    return out


def load_canonical_data() -> CanonicalData:
    """
    Load canonical EDCM bone data.

    The edcmbone package (installed from The-Interdependency/edcmbone) ships Python
    scaffolding and the canonical data zip at backend/data/edcmbone_canon_data_v1.zip.
    We first attempt to locate data via the installed package's __file__ path, then
    fall back to the bundled zip path. All four JSON files are validated against
    _meta.version before use. Raises CanonLoadError on failure.
    """
    try:
        import edcmbone as _edcmbone_pkg
        _pkg_dir = Path(_edcmbone_pkg.__file__).parent.parent
        _candidate = _pkg_dir / "edcmbone_canon_data_v1.zip"
        if not _candidate.exists():
            _candidate = _ZIP_PATH
    except ImportError:
        _candidate = _ZIP_PATH

    if not _candidate.exists():
        raise CanonLoadError(
            f"edcmbone canonical zip not found at {_candidate}. "
            "Cannot start without canonical data."
        )

    with zipfile.ZipFile(_candidate) as zf:
        words_data = _load_json_from_zip(zf, "bones_words_v1.json")
        affixes_data = _load_json_from_zip(zf, "bones_affixes_v1.json")
        punct_data = _load_json_from_zip(zf, "bones_punct_v1.json")
        markers_data = _load_json_from_zip(zf, "markers_v1.json")

    versions = {
        "bones_words": _validate_meta(words_data, "bones_words_v1.json"),
        "bones_affixes": _validate_meta(affixes_data, "bones_affixes_v1.json"),
        "bones_punct": _validate_meta(punct_data, "bones_punct_v1.json"),
        "markers": _validate_meta(markers_data, "markers_v1.json"),
    }

    word_to_primary, word_to_families, multiword_joins = _build_word_lookups(words_data)
    inflectional, dp, ds = _build_affix_lookups(affixes_data)
    punct_rules = _build_punct_rules(punct_data)
    markers_by_metric = _build_markers(markers_data)

    return CanonicalData(
        word_to_primary=word_to_primary,
        word_to_families=word_to_families,
        multiword_joins=multiword_joins,
        inflectional_affixes=inflectional,
        derivational_prefixes=dp,
        derivational_suffixes=ds,
        punct_rules=punct_rules,
        markers_by_metric=markers_by_metric,
        versions=versions,
    )


_CANON: CanonicalData | None = None


def get_canon() -> CanonicalData:
    global _CANON
    if _CANON is None:
        _CANON = load_canonical_data()
    return _CANON

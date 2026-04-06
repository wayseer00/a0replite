from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import edcmbone
from edcmbone import CanonLoadError  # re-exported for callers

# The installed edcmbone package (from The-Interdependency/edcmbone) ships only
# Python scaffolding (an empty __init__ and a placeholder parser stub).  It does
# NOT bundle the canonical zip as a package-data file.  The project therefore ships
# the zip at backend/data/ as the authoritative data source.  All parsing and
# validation is delegated to edcmbone.load_canonical_data() — this module's only
# role is to resolve the zip path and wrap the returned CanonData in CanonicalData.
_ZIP_PATH = Path(__file__).parent.parent.parent / "data" / "edcmbone_canon_data_v1.zip"


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


def load_canonical_data() -> CanonicalData:
    """
    Load EDCM canonical bone data via the ``edcmbone`` package public API.

    The zip path is resolved from ``backend/data/edcmbone_canon_data_v1.zip``.
    All parsing and validation is delegated to :func:`edcmbone.load_canonical_data`.
    Raises :class:`edcmbone.CanonLoadError` on any failure.
    """
    raw: edcmbone.CanonData = edcmbone.load_canonical_data(_ZIP_PATH)
    return CanonicalData(
        word_to_primary=raw.word_to_primary,
        word_to_families=raw.word_to_families,
        multiword_joins=raw.multiword_joins,
        inflectional_affixes=raw.inflectional_affixes,
        derivational_prefixes=raw.derivational_prefixes,
        derivational_suffixes=raw.derivational_suffixes,
        punct_rules=raw.punct_rules,
        markers_by_metric=raw.markers_by_metric,
        versions=raw.versions,
    )


_CANON: CanonicalData = load_canonical_data()


def get_canon() -> CanonicalData:
    return _CANON

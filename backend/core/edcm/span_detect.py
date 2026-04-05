from __future__ import annotations

import re
from dataclasses import dataclass

from core.edcm.data_loader import CanonicalData


@dataclass
class MarkerHit:
    marker_text: str
    metric: str
    marker_type: str
    turn_id: str
    char_position: int


def detect_spans(normalized_text: str, canon: CanonicalData, turn_id: str) -> list[MarkerHit]:
    """
    Scan normalized_text for all behavioral markers.
    Returns MarkerHit for every match.
    Markers are matched case-insensitively on the already-normalized text.
    """
    hits: list[MarkerHit] = []
    lowered = normalized_text.lower()

    for metric_id, metric_info in canon.markers_by_metric.items():
        for marker_type, marker_list in metric_info.get("marker_lists", {}).items():
            for marker in marker_list:
                marker_lower = marker.lower()
                start = 0
                while True:
                    pos = lowered.find(marker_lower, start)
                    if pos == -1:
                        break
                    hits.append(
                        MarkerHit(
                            marker_text=marker,
                            metric=metric_id,
                            marker_type=marker_type,
                            turn_id=turn_id,
                            char_position=pos,
                        )
                    )
                    start = pos + 1

    return hits

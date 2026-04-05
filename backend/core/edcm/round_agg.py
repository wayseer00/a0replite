from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.edcm.span_detect import MarkerHit


@dataclass
class RoundAggregates:
    by_metric: dict[str, dict[str, int]] = field(default_factory=dict)
    total_turns: int = 0
    total_tokens: int = 0

    def count(self, metric: str, marker_type: str) -> int:
        return self.by_metric.get(metric, {}).get(marker_type, 0)

    def total_for_metric(self, metric: str) -> int:
        return sum(self.by_metric.get(metric, {}).values())

    def as_dict(self) -> dict:
        return {
            "by_metric": dict(self.by_metric),
            "total_turns": self.total_turns,
            "total_tokens": self.total_tokens,
        }


def aggregate_round(marker_hits: list[MarkerHit], total_turns: int = 0, total_tokens: int = 0) -> RoundAggregates:
    """Group marker hits by metric and marker_type."""
    by_metric: dict[str, dict[str, int]] = {}
    for hit in marker_hits:
        if hit.metric not in by_metric:
            by_metric[hit.metric] = {}
        by_metric[hit.metric][hit.marker_type] = by_metric[hit.metric].get(hit.marker_type, 0) + 1
    return RoundAggregates(by_metric=by_metric, total_turns=total_turns, total_tokens=total_tokens)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.edcm.data_loader import CanonicalData
from core.edcm.round_agg import RoundAggregates
from core.edcm.turn_agg import OperatorVector

_SOURCE_FILES = ("bones_words_v1.json", "bones_affixes_v1.json", "markers_v1.json")


@dataclass
class BehavioralVector:
    R: float = 0.0
    L: float = 0.0
    N: float = 0.0
    E: float = 0.0
    C: Optional[float] = None
    D: Optional[float] = None
    O: Optional[float] = None
    F: None = None
    I: None = None
    partial_metrics: list[str] = field(default_factory=list)
    requires_embeddings: bool = True
    data_version: str = "1.0.0"
    source_files: tuple = _SOURCE_FILES
    hmmm: str = ""

    def as_dict(self) -> dict:
        return {
            "R": self.R, "L": self.L, "N": self.N, "E": self.E,
            "C": self.C, "D": self.D, "O": self.O, "F": None, "I": None,
            "partial_metrics": list(self.partial_metrics),
            "requires_embeddings": self.requires_embeddings,
            "data_version": self.data_version,
            "source_files": list(self.source_files),
            "hmmm": self.hmmm,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BehavioralVector":
        return cls(
            R=float(d.get("R", 0.0)),
            L=float(d.get("L", 0.0)),
            N=float(d.get("N", 0.0)),
            E=float(d.get("E", 0.0)),
            C=float(d["C"]) if d.get("C") is not None else None,
            D=float(d["D"]) if d.get("D") is not None else None,
            O=float(d["O"]) if d.get("O") is not None else None,
            F=None,
            I=None,
            partial_metrics=list(d.get("partial_metrics", [])),
            requires_embeddings=bool(d.get("requires_embeddings", True)),
            data_version=str(d.get("data_version", "1.0.0")),
            source_files=tuple(d.get("source_files", _SOURCE_FILES)),
            hmmm=str(d.get("hmmm", "")),
        )


@dataclass
class BridgeMatrix:
    matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    data_version: str = "1.0.0"
    source_files: tuple = _SOURCE_FILES
    hmmm: str = ""

    def as_dict(self) -> dict:
        return {
            "matrix": {k: dict(v) for k, v in self.matrix.items()},
            "data_version": self.data_version,
            "source_files": list(self.source_files),
            "hmmm": self.hmmm,
        }


def _safe_ratio(num: float, denom: float) -> float:
    return num / denom if denom else 0.0


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation between two equal-length lists."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    denom = sx * sy
    return cov / denom if denom else 0.0


def compute_behavioral_vector(
    round_aggs: RoundAggregates,
    operator_vectors: list[OperatorVector],
    canon: CanonicalData,
) -> BehavioralVector:
    """
    Compute the 9-metric behavioral vector from round aggregates and operator vectors.
    F and I always return None with requires_embeddings=True.
    C, D, O are partial: marker-based estimation, requires_embeddings=True flagged.
    """
    partial = []

    total_turns = round_aggs.total_turns or max(len(operator_vectors), 1)
    total_tokens = round_aggs.total_tokens or 1

    r_num = round_aggs.count("R", "refusal") + round_aggs.count("R", "soft_refusal")
    r_denom = max(1, round_aggs.count("R", "constraint_statement") + round_aggs.count("R", "request"))
    R = _safe_ratio(r_num, r_denom)

    L_raw = round_aggs.count("L", "load_amplifier") + round_aggs.count("L", "constraint_statement") + round_aggs.count("R", "constraint_statement")
    L = float(L_raw)

    n_num = round_aggs.count("N", "resolution")
    N = _safe_ratio(n_num, max(1.0, L))

    tier_map = {"low": 0, "medium": 1, "high": 2}
    prev_tier = -1
    escalation = 0
    for metric_type in ("commitment_low", "commitment_medium", "commitment_high"):
        tier_label = metric_type.split("_", 1)[1]
        tier_val = tier_map.get(tier_label, 0)
        count = round_aggs.count("E", metric_type) or round_aggs.total_for_metric("E")
        if count > 0 and tier_val > prev_tier:
            escalation += max(0, tier_val - prev_tier)
            prev_tier = tier_val
    E = float(escalation)

    c_num = round_aggs.count("C", "explicit_contradiction") + round_aggs.count("C", "self_correction")
    C = _safe_ratio(c_num, total_turns)
    partial.append("C")

    d_num = (round_aggs.count("D", "topic_shift") + round_aggs.count("D", "evasion") + round_aggs.count("D", "vague_response"))
    D = _safe_ratio(d_num, total_tokens)
    partial.append("D")

    o_expansion = round_aggs.count("O", "scope_expansion")
    o_containment = round_aggs.count("O", "scope_containment")
    O = _safe_ratio(o_expansion, max(1, o_expansion + o_containment))
    partial.append("O")

    return BehavioralVector(
        R=R, L=L, N=N, E=E, C=C, D=D, O=O,
        F=None, I=None,
        partial_metrics=partial,
        requires_embeddings=True,
        hmmm="",
    )


def metrics_snapshot(behavioral_vec: "BehavioralVector") -> dict:
    """Return behavioral vector as a plain dict snapshot."""
    return behavioral_vec.as_dict()


def compute_bridge(
    operator_history: list[OperatorVector],
    behavioral_history: list[BehavioralVector],
) -> BridgeMatrix:
    """
    Compute Pearson correlation between each O_family and each B_metric
    over the last min(N, 10) rounds.
    """
    n = min(len(operator_history), len(behavioral_history), 10)
    if n < 2:
        return BridgeMatrix(hmmm="")

    o_hist = operator_history[-n:]
    b_hist = behavioral_history[-n:]

    families = ("P", "K", "Q", "T", "S")
    b_metrics = ("R", "L", "N", "E", "C", "D", "O")

    matrix: dict[str, dict[str, float]] = {}
    for fam in families:
        matrix[fam] = {}
        xs = [getattr(ov, fam) for ov in o_hist]
        for bm in b_metrics:
            ys_raw = [getattr(bv, bm) for bv in b_hist]
            if any(y is None for y in ys_raw):
                matrix[fam][bm] = 0.0
            else:
                matrix[fam][bm] = _pearson(xs, [float(y) for y in ys_raw])

    return BridgeMatrix(matrix=matrix, hmmm="")

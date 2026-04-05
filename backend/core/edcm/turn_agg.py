from __future__ import annotations

from dataclasses import dataclass

from core.edcm.bone_match import BoneToken


@dataclass
class OperatorVector:
    P: int = 0
    K: int = 0
    Q: int = 0
    T: int = 0
    S: int = 0
    total: int = 0

    def as_dict(self) -> dict:
        return {"P": self.P, "K": self.K, "Q": self.Q, "T": self.T, "S": self.S, "total": self.total}


def aggregate_turn(bone_tokens: list[BoneToken]) -> OperatorVector:
    """Count bone tokens per PKQTS family and return an OperatorVector."""
    vec = OperatorVector()
    for bt in bone_tokens:
        f = bt.family.upper()
        if f == "P":
            vec.P += 1
        elif f == "K":
            vec.K += 1
        elif f == "Q":
            vec.Q += 1
        elif f == "T":
            vec.T += 1
        elif f == "S":
            vec.S += 1
        vec.total += 1
    return vec

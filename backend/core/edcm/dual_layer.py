from __future__ import annotations

from typing import Any, Optional

from core.edcm.metrics import BehavioralVector
from core.edcm.zeta_parser import ZetaParser


class DualLayerEDCM:
    """
    Dual-layer EDCM:
    Layer 1 (Zeta) — in-house Zeta parser against canonical edcmbone data.
    Layer 2 (Metrics) — quantitative C/R/D/N/L/O/F/E/I metrics.

    aimmh_lib's built-in EDCM service uses old CM/DA/DRIFT signals; we ignore it.
    """

    def __init__(self, parser: ZetaParser) -> None:
        self._parser = parser

    def layer1_validate(self, document_name: str, response_text: str) -> dict:
        """
        Layer 1: Zeta-signal validation against canonical document.
        Returns dict with canonical excerpt and any violated signals.
        """
        doc = self._parser.get(document_name)
        if doc is None:
            return {
                "valid": False,
                "reason": f"Document {document_name!r} not found in canonical corpus",
                "signals_checked": [],
            }

        violations = []
        for label, canonical_val in doc.signals.items():
            if canonical_val and canonical_val.lower() not in response_text.lower():
                violations.append({"signal": label, "expected_fragment": canonical_val[:120]})

        return {
            "valid": len(violations) == 0,
            "document": document_name,
            "signals_checked": list(doc.signals.keys()),
            "violations": violations,
        }

    def layer2_metrics(
        self,
        R: float = 0.0,
        L: float = 0.0,
        N: float = 0.0,
        E: float = 0.0,
        C: Optional[float] = None,
        D: Optional[float] = None,
        O: Optional[float] = None,
    ) -> dict:
        """Layer 2: return C/R/D/N/L/O/F/E/I metrics snapshot from a BehavioralVector."""
        bv = BehavioralVector(R=R, L=L, N=N, E=E, C=C, D=D, O=O)
        return bv.as_dict()

    def evaluate(self, document_name: str, response_text: str, **metric_kwargs: Any) -> dict:
        """Run both layers and return combined evaluation."""
        l1 = self.layer1_validate(document_name, response_text)
        l2 = self.layer2_metrics(**metric_kwargs)
        return {"layer1": l1, "layer2": l2, "overall_valid": l1["valid"]}

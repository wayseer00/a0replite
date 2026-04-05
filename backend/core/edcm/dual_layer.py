from __future__ import annotations

from typing import Any, Optional

from core.edcm.metrics import metrics_snapshot
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
        context_vector: list[float],
        facts_recalled: int,
        facts_available: int,
        drift_tokens: int,
        total_tokens: int,
        novel_claims: int,
        total_claims: int,
        latency_ms: float,
        baseline_ms: float = 1000.0,
        scope_tokens_used: int = 0,
        scope_total: int = 4096,
        embedding: Optional[list[float]] = None,
        canonical_embedding: Optional[list[float]] = None,
        off_topic_center: Optional[list[float]] = None,
        instruction_embedding: Optional[list[float]] = None,
    ) -> dict:
        """Layer 2: return C/R/D/N/L/O/F/E/I metrics snapshot."""
        return metrics_snapshot(
            context_vector=context_vector,
            facts_recalled=facts_recalled,
            facts_available=facts_available,
            drift_tokens=drift_tokens,
            total_tokens=total_tokens,
            novel_claims=novel_claims,
            total_claims=total_claims,
            latency_ms=latency_ms,
            baseline_ms=baseline_ms,
            scope_tokens_used=scope_tokens_used,
            scope_total=scope_total,
            embedding=embedding,
            canonical_embedding=canonical_embedding,
            off_topic_center=off_topic_center,
            instruction_embedding=instruction_embedding,
        )

    def evaluate(self, document_name: str, response_text: str, **metric_kwargs: Any) -> dict:
        """Run both layers and return combined evaluation."""
        l1 = self.layer1_validate(document_name, response_text)
        l2 = self.layer2_metrics(**metric_kwargs)
        return {"layer1": l1, "layer2": l2, "overall_valid": l1["valid"]}

from __future__ import annotations

import math
from typing import Any, Optional


def _safe_ratio(a: float, b: float) -> float:
    return a / b if b else 0.0


def compute_C(context_vector: list[float]) -> float:
    """C — Coherence: mean cosine self-similarity of context token vectors."""
    if not context_vector:
        return 0.0
    n = len(context_vector)
    norm = math.sqrt(sum(x * x for x in context_vector)) or 1.0
    return sum(x / norm for x in context_vector) / n


def compute_R(facts_recalled: int, facts_available: int) -> float:
    """R — Retention: fraction of available facts recalled."""
    return _safe_ratio(facts_recalled, facts_available)


def compute_D(drift_tokens: int, total_tokens: int) -> float:
    """D — Drift: fraction of tokens that deviated from canonical."""
    return _safe_ratio(drift_tokens, total_tokens)


def compute_N(novel_claims: int, total_claims: int) -> float:
    """N — Novelty: fraction of genuinely novel (non-canonical) claims."""
    return _safe_ratio(novel_claims, total_claims)


def compute_L(latency_ms: float, baseline_ms: float) -> float:
    """L — Latency ratio: actual / baseline. 1.0 = on target, >1.0 = slow."""
    return _safe_ratio(latency_ms, baseline_ms) if baseline_ms > 0 else 0.0


def compute_O(scope_tokens_used: int, scope_total: int) -> float:
    """O — Overreach: fraction of scope budget consumed."""
    return _safe_ratio(scope_tokens_used, scope_total)


def compute_F(embedding: Optional[list[float]], canonical_embedding: Optional[list[float]]) -> Optional[float]:
    """F — Fidelity: cosine similarity to canonical document embedding. Requires embeddings."""
    if embedding is None or canonical_embedding is None:
        return None
    dot = sum(a * b for a, b in zip(embedding, canonical_embedding))
    na = math.sqrt(sum(x * x for x in embedding)) or 1.0
    nb = math.sqrt(sum(x * x for x in canonical_embedding)) or 1.0
    return dot / (na * nb)


def compute_E(embedding: Optional[list[float]], off_topic_center: Optional[list[float]]) -> Optional[float]:
    """E — Embedding drift from off-topic center: cosine similarity (lower = better)."""
    return compute_F(embedding, off_topic_center)


def compute_I(
    response_embedding: Optional[list[float]],
    instruction_embedding: Optional[list[float]],
) -> Optional[float]:
    """I — Instruction following fidelity: cosine similarity between response and instruction."""
    return compute_F(response_embedding, instruction_embedding)


def metrics_snapshot(
    context_vector: list[float],
    facts_recalled: int,
    facts_available: int,
    drift_tokens: int,
    total_tokens: int,
    novel_claims: int,
    total_claims: int,
    latency_ms: float,
    baseline_ms: float,
    scope_tokens_used: int,
    scope_total: int,
    embedding: Optional[list[float]] = None,
    canonical_embedding: Optional[list[float]] = None,
    off_topic_center: Optional[list[float]] = None,
    instruction_embedding: Optional[list[float]] = None,
) -> dict:
    f = compute_F(embedding, canonical_embedding)
    e = compute_E(embedding, off_topic_center)
    i = compute_I(embedding, instruction_embedding)
    requires_embeddings = embedding is None
    return {
        "C": compute_C(context_vector),
        "R": compute_R(facts_recalled, facts_available),
        "D": compute_D(drift_tokens, total_tokens),
        "N": compute_N(novel_claims, total_claims),
        "L": compute_L(latency_ms, baseline_ms),
        "O": compute_O(scope_tokens_used, scope_total),
        "F": f,
        "E": e,
        "I": i,
        "requires_embeddings": requires_embeddings,
    }

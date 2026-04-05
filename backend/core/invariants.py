from __future__ import annotations


class InvariantViolation(Exception):
    """Raised when the hmmm invariant is missing from an event dict."""


def require_hmmm(d: dict, context: str = "") -> None:
    """Law 14: missing invariant fails closed."""
    if not isinstance(d, dict) or "hmmm" not in d or d["hmmm"] is None:
        suffix = f": {context}" if context else ""
        raise InvariantViolation(f"Missing hmmm invariant{suffix}")

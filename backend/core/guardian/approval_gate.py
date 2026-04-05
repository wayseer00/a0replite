from __future__ import annotations

import os
from typing import Any

VALID_GATES = frozenset(
    {"PUBLISH", "PUSH", "MODIFY_SECRETS", "SPEND_FUNDS", "EXECUTE_MONETIZATION"}
)

_PUSH_GATES = frozenset({"PUSH", "PUBLISH", "MODIFY_SECRETS"})


class GateRejected(Exception):
    """Raised when an approval gate is not satisfied (S4 not approved)."""


def check_gate(gate_name: str, inst: Any) -> None:
    """
    Verify S4 approval before allowing a named external effect.
    Law 8: capability is not authority. Law 12: external effects require approval.

    For PUSH-class gates (PUSH, PUBLISH, MODIFY_SECRETS), approval requires BOTH:
    1. inst.approved == True (session-level S4 approval), AND
    2. GUARDIAN_OPERATOR_KEY set in environment (runtime owner authorization signal).
    This prevents pre-authorized system instances from autonomously executing
    external write effects without explicit operator key presence.
    """
    if gate_name not in VALID_GATES:
        raise GateRejected(f"Unknown gate: {gate_name!r}")
    approved = getattr(inst, "approved", False)
    if not approved:
        raise GateRejected(
            f"Gate {gate_name!r} rejected: S4 not approved. "
            "Owner must authorize this action via ZFAE."
        )
    if gate_name in _PUSH_GATES:
        operator_key = os.environ.get("GUARDIAN_OPERATOR_KEY", "").strip()
        if not operator_key:
            raise GateRejected(
                f"Gate {gate_name!r} rejected: GUARDIAN_OPERATOR_KEY not set. "
                "Runtime owner authorization required for external write effects."
            )


def pre_authorize_boot(inst: Any) -> None:
    """Pre-authorize the boot task. Called once at startup by the deploy invocation."""
    inst.approve(reason="boot_pre_authorized_by_deploy")

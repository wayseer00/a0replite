from __future__ import annotations

from typing import Any

VALID_GATES = frozenset(
    {"PUBLISH", "PUSH", "MODIFY_SECRETS", "SPEND_FUNDS", "EXECUTE_MONETIZATION"}
)


class GateRejected(Exception):
    """Raised when an approval gate is not satisfied (S4 not approved)."""


def check_gate(gate_name: str, inst: Any) -> None:
    """
    Verify S4 approval before allowing a named external effect.
    Law 8: capability is not authority. Law 12: external effects require approval.
    Gate passes iff inst.approved is True (S4 pre-authorization).
    """
    if gate_name not in VALID_GATES:
        raise GateRejected(f"Unknown gate: {gate_name!r}")
    approved = getattr(inst, "approved", False)
    if not approved:
        raise GateRejected(
            f"Gate {gate_name!r} rejected: S4 not approved. "
            "Owner must authorize this action via ZFAE."
        )


def pre_authorize_boot(inst: Any) -> None:
    """Pre-authorize the boot task. Called once at startup by the deploy invocation."""
    inst.approve(reason="boot_pre_authorized_by_deploy")

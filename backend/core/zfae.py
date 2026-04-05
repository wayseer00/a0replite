from __future__ import annotations

from typing import Any

from core.guardian.approval_gate import GateRejected, check_gate


class ZFAEGatekeeper:
    """
    Zero-Frame Authority Enforcement — infers behavioral identity from context signals.
    Phone channel → owner authority → sets S4 approved.
    Suspicious pattern → revokes S4.
    """

    def __init__(self, inst: Any) -> None:
        self._inst = inst

    def infer_authority(self, request_context: dict) -> str:
        """
        Examine context signals and set S4 accordingly.
        Returns authority level: "owner", "suspect", or "standard".
        """
        if request_context.get("phone_channel") is True:
            self._inst.approve(reason="zfae_phone_channel_confirmed")
            return "owner"

        consistent = request_context.get("session_pattern_consistent", True)
        anomaly = float(request_context.get("anomaly_score", 0.0))
        if not consistent and anomaly > 0.7:
            self._inst.revoke(reason="zfae_anomaly_detected")
            return "suspect"

        return "standard"

    def guard_management_action(self, gate_name: str, request_context: dict) -> None:
        """Infer authority, then check the named gate against S4."""
        self.infer_authority(request_context)
        check_gate(gate_name, self._inst)

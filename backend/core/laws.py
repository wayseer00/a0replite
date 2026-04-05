from __future__ import annotations

from core.invariants import InvariantViolation, require_hmmm


class LawViolation(Exception):
    """Raised when a Law is violated."""


def law3_volatile_not_committed(task_id: str, volatile_ids: set, committed_ids: set) -> None:
    """Law 3: volatile state must not appear in the committed store."""
    if task_id in committed_ids:
        raise LawViolation(f"Law 3: task {task_id!r} is volatile but found in committed store")


def law4_persistence_requires_adjudication(event: dict, adjudicator_id: str) -> None:
    """Law 4: persistence requires an adjudicator to be named."""
    if not adjudicator_id or adjudicator_id.strip() == "":
        raise LawViolation(f"Law 4: event {event.get('event_type','?')} has no adjudicator")


def law6_quarantine_over_collapse(exc: Exception, context: str, inst: object = None) -> None:
    """
    Law 6: quarantine over collapse — isolate the error, log it, never re-raise.
    Delegates to recovery.quarantine(). Does not cascade. Does not crash the process.
    """
    from core.guardian.recovery import quarantine
    quarantine(exc, context, inst)


def law8_capability_not_authority(gate_name: str, s4_approved: bool) -> None:
    """Law 8: capability (gate exists) does not confer authority (S4 must be approved)."""
    if not s4_approved:
        raise LawViolation(
            f"Law 8: gate {gate_name!r} capability present but S4 not approved — "
            "capability is not authority"
        )


def law11_logs_not_memory(task_id: str, volatile_queue: dict, db_ids: set) -> None:
    """Law 11: a volatile task that completed must not persist in committed DB."""
    if task_id in db_ids:
        raise LawViolation(
            f"Law 11: task {task_id!r} is a log artifact (volatile) but found in memory store"
        )


def law12_external_effects_require_approval(gate_name: str, s4_approved: bool) -> None:
    """Law 12: any external effect requires prior approval gate passage."""
    law8_capability_not_authority(gate_name, s4_approved)


def law14_missing_invariant_fails_closed(d: dict, context: str = "") -> None:
    """Law 14: missing hmmm invariant fails closed (delegates to require_hmmm)."""
    require_hmmm(d, context)

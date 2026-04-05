from __future__ import annotations

from enum import Enum


class InstanceState(Enum):
    INIT = "init"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    SHUTDOWN = "shutdown"


_VALID_TRANSITIONS = {
    InstanceState.INIT: {InstanceState.ACTIVE},
    InstanceState.ACTIVE: {InstanceState.SUSPENDED, InstanceState.SHUTDOWN},
    InstanceState.SUSPENDED: {InstanceState.RESUMED},
    InstanceState.RESUMED: {InstanceState.ACTIVE, InstanceState.SHUTDOWN},
    InstanceState.SHUTDOWN: set(),
}


class InvalidTransition(Exception):
    pass


class InstanceLifecycle:
    def __init__(self) -> None:
        self._state = InstanceState.INIT

    @property
    def state(self) -> InstanceState:
        return self._state

    def transition(self, target: InstanceState) -> None:
        allowed = _VALID_TRANSITIONS.get(self._state, set())
        if target not in allowed:
            raise InvalidTransition(
                f"Invalid transition {self._state.value} → {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        self._state = target

    def activate(self) -> None:
        if self._state in (InstanceState.INIT, InstanceState.RESUMED):
            self._state = InstanceState.ACTIVE

    def suspend(self) -> None:
        self.transition(InstanceState.SUSPENDED)

    def resume(self) -> None:
        self.transition(InstanceState.RESUMED)
        self._state = InstanceState.ACTIVE

    def shutdown(self) -> None:
        if self._state != InstanceState.SHUTDOWN:
            self._state = InstanceState.SHUTDOWN

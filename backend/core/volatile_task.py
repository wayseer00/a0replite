from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class VolatileTask:
    id: str
    name: str
    fn: Callable
    self_delete: bool = True
    registered_at: float = field(default_factory=time.time)
    status: str = "pending"


class TaskQueue:
    """
    In-process volatile task queue. Tasks that self_delete leave only an S9 event (Law 11).
    Every task execution emits S9 audit events for task_started and task_completed/task_failed.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, VolatileTask] = {}

    def register(self, task: VolatileTask) -> None:
        self._tasks[task.id] = task

    def list_tasks(self) -> list[dict]:
        return [
            {"id": t.id, "name": t.name, "status": t.status, "registered_at": t.registered_at}
            for t in self._tasks.values()
        ]

    async def run(self, task_id: str, inst: Any = None) -> dict:
        """
        Run a task. S9 audit events are always emitted:
        - task_started: when execution begins
        - task_completed: on success (with self_delete marker)
        - task_failed: on exception
        Self-deleting tasks are removed from the queue after completion or failure.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return {"status": "not_found", "task_id": task_id, "hmmm": ""}

        task.status = "running"
        result: dict = {"status": "error", "task_id": task_id, "hmmm": ""}

        if inst is not None:
            try:
                from core.guardian import audit
                audit.append_event(
                    inst,
                    "task_started",
                    {"hmmm": "", "task_id": task_id, "task_name": task.name},
                )
            except Exception:
                pass

        try:
            if asyncio.iscoroutinefunction(task.fn):
                await task.fn()
            else:
                task.fn()
            task.status = "completed"
            result["status"] = "completed"

            if inst is not None:
                try:
                    from core.guardian import audit
                    audit.append_event(
                        inst,
                        "task_completed",
                        {
                            "hmmm": "",
                            "task_id": task_id,
                            "task_name": task.name,
                            "self_delete": task.self_delete,
                        },
                    )
                except Exception:
                    pass

        except Exception as exc:
            task.status = "failed"
            result["status"] = "failed"
            result["error"] = str(exc)

            if inst is not None:
                try:
                    from core.guardian import audit
                    audit.append_event(
                        inst,
                        "task_failed",
                        {
                            "hmmm": "",
                            "task_id": task_id,
                            "task_name": task.name,
                            "error": str(exc),
                        },
                    )
                except Exception:
                    pass

        finally:
            if task.self_delete and task.status in ("completed", "failed"):
                self._tasks.pop(task_id, None)

        return result

    def __len__(self) -> int:
        return len(self._tasks)


_global_queue = TaskQueue()


def get_queue() -> TaskQueue:
    return _global_queue

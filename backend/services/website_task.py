from __future__ import annotations

"""
Deprecated stub — website repair is handled by core.boot_task with S4 (PUSH) gate check.
All pushes to wayseer.github.io require prior owner approval via ZFAE (Law 8 / Law 12).
Direct self-authorizing pushes are prohibited.
"""

from core.boot_task import make_boot_task, run_boot_task

__all__ = ["make_boot_task", "run_boot_task"]

from __future__ import annotations

import sys
import time
import traceback
from typing import Any, Optional


def quarantine(exc: Exception, context: str, inst: Any = None) -> None:
    """
    Law 6: quarantine over collapse. Isolate the error, log it, never re-raise.
    Does not cascade. Does not crash the process.
    """
    tb = traceback.format_exc()
    msg = (
        f"[QUARANTINE] context={context!r} "
        f"exc_type={type(exc).__name__} "
        f"exc={exc!r} "
        f"ts={time.time():.3f}"
    )
    print(msg, file=sys.stderr)
    if tb and tb.strip() != "NoneType: None":
        print(tb, file=sys.stderr)

    if inst is not None:
        try:
            from core.guardian import audit
            audit.append_event(
                inst,
                "quarantine",
                {
                    "context": context,
                    "exc_type": type(exc).__name__,
                    "exc_message": str(exc),
                    "hmmm": "",
                },
            )
        except Exception as audit_exc:
            print(f"[QUARANTINE] audit append failed: {audit_exc!r}", file=sys.stderr)

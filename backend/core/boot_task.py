from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from core.guardian import audit
from core.guardian.approval_gate import check_gate
from core.guardian.recovery import quarantine
from core.volatile_task import VolatileTask

_IDENTITY_SPEC = """
Visual identity for wayseer.github.io:
- Background: #0a0a0f (near-black)
- Accent/primary: #00f0ff (cyan)
- Secondary accent: #8b5cf6 (violet)
- Animation: tensor field animation (canvas-based, low-opacity)
- Navigation: frosted glass (backdrop-filter: blur)
- Wordmark: "INTERDEPENDENT" — uppercase, letter-spaced
- Font: Inter (Google Fonts)
- Aesthetic: dark, contemplative, grounded
"""

_PATCH_PROMPT = (
    "Compare these files against the canonical visual identity specification. "
    "Produce a minimal patch set as a JSON array. Each element must be: "
    '{"path": "<file_path>", "content": "<full_file_content_as_string>"}. '
    "Only include files that need changes. Respond with valid JSON only."
)


async def run_boot_task(inst: Any, grok_call_fn: Callable, github_token: str) -> None:
    """
    Autonomous website repair boot task.
    1. Check S4 gate (PUSH).
    2. Fetch all web files from wayseer.github.io.
    3. Ask Grok for a patch set.
    4. Apply patches.
    5. Verify commit SHA.
    6. Record in S9.
    7. Self-delete from volatile queue.
    """
    try:
        check_gate("PUSH", inst)
    except Exception as exc:
        quarantine(exc, "boot_task:gate_check", inst)
        return

    try:
        from services.github import fetch_file, get_repo_tree, get_default_branch_sha, push_file

        tree = await get_repo_tree(github_token)
        target_exts = {".html", ".css", ".md"}
        target_files = [
            item for item in tree
            if item.get("type") == "blob"
            and any(item.get("path", "").endswith(ext) for ext in target_exts)
        ][:12]

        file_contents: dict[str, str] = {}
        file_shas: dict[str, str] = {}
        for item in target_files:
            path = item["path"]
            file_shas[path] = item.get("sha", "")
            try:
                file_contents[path] = await fetch_file(path, github_token)
            except Exception as exc:
                quarantine(exc, f"boot_task:fetch:{path}", inst)

        files_block = "\n\n".join(
            f"=== {path} ===\n{content[:2000]}"
            for path, content in file_contents.items()
        )
        prompt = f"{_IDENTITY_SPEC}\n\n{files_block}\n\n{_PATCH_PROMPT}"

        response = await grok_call_fn("grok-3", [{"role": "user", "content": prompt}])
        patches = _extract_patches(response)

        patches_applied = 0
        for patch in patches:
            path = patch.get("path", "")
            content = patch.get("content", "")
            sha = file_shas.get(path, "")
            if not path or not content or not sha:
                continue
            try:
                await push_file(
                    path=path,
                    content=content,
                    sha=sha,
                    github_token=github_token,
                    commit_message="chore: a0replite boot visual identity patch",
                )
                patches_applied += 1
            except Exception as exc:
                quarantine(exc, f"boot_task:push:{path}", inst)

        commit_sha = await get_default_branch_sha(github_token)

        audit.append_event(
            inst,
            "boot_task_complete",
            {
                "patches_applied": patches_applied,
                "commit_sha": commit_sha,
                "hmmm": "",
            },
        )
    except Exception as exc:
        quarantine(exc, "boot_task", inst)


def _extract_patches(response: str) -> list[dict]:
    """Extract JSON patch list from Grok response."""
    try:
        json_match = re.search(r"\[.*?\]", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(response.strip())
    except Exception:
        return []


def make_boot_task(inst: Any, grok_call_fn: Callable, github_token: str) -> VolatileTask:
    """Create a self-deleting boot task for website repair."""
    import uuid

    async def _run() -> None:
        await run_boot_task(inst, grok_call_fn, github_token)

    return VolatileTask(
        id=f"boot-task-{uuid.uuid4()}",
        name="website_repair",
        fn=_run,
        self_delete=True,
    )

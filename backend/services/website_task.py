from __future__ import annotations

import base64
import os
from typing import Any

import httpx

_WAYSEER_REPO_API = "https://api.github.com/repos/wayseer00/wayseer.github.io"
_DEFAULT_HEADERS = {"Accept": "application/vnd.github.v3+json", "X-GitHub-Api-Version": "2022-11-28"}


def _gh_headers(token: str) -> dict:
    return {**_DEFAULT_HEADERS, "Authorization": f"Bearer {token}"}


async def repair_website() -> dict:
    """
    Self-authorizing autonomous boot task:
    1. Fetch wayseer.github.io index.html
    2. If broken (HTTP ≥ 400 or empty), push a minimal repair commit
    3. Self-delete: return 'self_delete': True to instruct the queue to remove the task
    """
    token = os.environ.get("GITHUB_TOKEN_WAYSEER00", "")
    if not token:
        return {
            "status": "skipped",
            "reason": "GITHUB_TOKEN_WAYSEER00 not set",
            "self_delete": True,
        }

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Check site health
        try:
            site_resp = await client.get("https://wayseer00.github.io/", follow_redirects=True)
            site_ok = site_resp.status_code < 400 and len(site_resp.text.strip()) > 64
        except Exception:
            site_ok = False

        if site_ok:
            return {
                "status": "healthy",
                "reason": "Site is already serving correctly — no repair needed",
                "self_delete": True,
            }

        # Fetch current index.html SHA for update
        headers = _gh_headers(token)
        file_resp = await client.get(f"{_WAYSEER_REPO_API}/contents/index.html", headers=headers)
        sha = None
        if file_resp.status_code == 200:
            sha = file_resp.json().get("sha")

        repair_html = _minimal_index_html()
        encoded = base64.b64encode(repair_html.encode()).decode()

        body: dict = {
            "message": "chore: a0replite boot repair — restore index",
            "content": encoded,
            "committer": {"name": "a0replite", "email": "a0@interdependentway.org"},
        }
        if sha:
            body["sha"] = sha

        push_resp = await client.put(
            f"{_WAYSEER_REPO_API}/contents/index.html",
            headers=headers,
            json=body,
        )
        push_resp.raise_for_status()

    return {
        "status": "repaired",
        "commit_url": push_resp.json().get("commit", {}).get("html_url", ""),
        "self_delete": True,
    }


def _minimal_index_html() -> str:
    return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The Interdependent Way</title>
  <style>
    body { margin: 0; background: #0f0f0f; color: #e0e0e0; font-family: Georgia, serif;
           display: flex; flex-direction: column; align-items: center; justify-content: center;
           min-height: 100vh; text-align: center; padding: 2rem; }
    h1 { font-size: 2.5rem; margin-bottom: 1rem; }
    p  { font-size: 1.2rem; max-width: 600px; line-height: 1.7; }
    a  { color: #8ab4f8; }
  </style>
</head>
<body>
  <h1>The Interdependent Way</h1>
  <p>
    This instance is grounded. We are at <a href="https://www.interdependentway.org">interdependentway.org</a>.
  </p>
  <p><em>Restored by a0replite autonomous boot task.</em></p>
</body>
</html>
"""

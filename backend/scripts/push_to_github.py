#!/usr/bin/env python3
"""
Create the wayseer00/a0replite GitHub repo and push backend code.
Requires GITHUB_TOKEN_WAYSEER00 environment variable.

Usage:
  python3 backend/scripts/push_to_github.py
"""
from __future__ import annotations

import os
import subprocess
import sys

import httpx

REPO_NAME = "a0replite"
OWNER = "wayseer00"
DESCRIPTION = "Grounded AI instance at interdependentway.org — PTCA/PCEA/EDCM backend"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def create_repo(token: str) -> str:
    """Create or confirm the repo. Returns clone URL."""
    resp = httpx.get(
        f"https://api.github.com/repos/{OWNER}/{REPO_NAME}",
        headers=_headers(token),
    )
    if resp.status_code == 200:
        print(f"Repo already exists: {resp.json()['html_url']}")
        return resp.json()["clone_url"]

    create_resp = httpx.post(
        "https://api.github.com/user/repos",
        headers=_headers(token),
        json={
            "name": REPO_NAME,
            "description": DESCRIPTION,
            "private": False,
            "auto_init": False,
        },
    )
    if create_resp.status_code not in (200, 201):
        print(f"Error creating repo: {create_resp.status_code} {create_resp.text}")
        sys.exit(1)
    url = create_resp.json()["clone_url"]
    print(f"Created repo: {create_resp.json()['html_url']}")
    return url


def git_push(clone_url: str, token: str) -> None:
    auth_url = clone_url.replace("https://", f"https://{token}@")
    cmds = [
        ["git", "init", "-b", "main"],
        ["git", "add", "."],
        ["git", "commit", "-m", "feat: initial a0replite backend commit"],
        ["git", "remote", "add", "origin", auth_url],
        ["git", "push", "-u", "origin", "main", "--force"],
    ]
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = result.stderr.replace(token, "***")
            print(f"Error running {cmd[0]} {cmd[1]}: {stderr}")
            sys.exit(1)
        print(f"✓ {' '.join(cmd[:2])}")


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN_WAYSEER00", "")
    if not token:
        print("Error: GITHUB_TOKEN_WAYSEER00 not set")
        sys.exit(1)
    clone_url = create_repo(token)
    git_push(clone_url, token)
    print(f"\n✓ Pushed to https://github.com/{OWNER}/{REPO_NAME}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
One-time setup script: create the wayseer00/a0replite repo and push via git credential helper.
Token is read from the GITHUB_TOKEN_WAYSEER00 environment variable and passed to git
via GIT_ASKPASS — it is never embedded in remote URLs.

Usage:
  GITHUB_TOKEN_WAYSEER00=<token> python3 backend/scripts/push_to_github.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import httpx

REPO_NAME = "a0replite"
OWNER = "wayseer00"
HTTPS_URL = f"https://github.com/{OWNER}/{REPO_NAME}.git"
DESCRIPTION = "Grounded AI instance at interdependentway.org — PTCA/PCEA/EDCM backend"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def create_repo(token: str) -> None:
    """Create or confirm the repo exists."""
    resp = httpx.get(
        f"https://api.github.com/repos/{OWNER}/{REPO_NAME}",
        headers=_headers(token),
    )
    if resp.status_code == 200:
        print(f"Repo exists: {resp.json()['html_url']}")
        return

    create_resp = httpx.post(
        "https://api.github.com/user/repos",
        headers=_headers(token),
        json={"name": REPO_NAME, "description": DESCRIPTION, "private": False, "auto_init": False},
    )
    if create_resp.status_code not in (200, 201):
        print(f"Error creating repo: {create_resp.status_code} {create_resp.text}")
        sys.exit(1)
    print(f"Created repo: {create_resp.json()['html_url']}")


def git_push(token: str) -> None:
    """
    Push to remote using a GIT_ASKPASS helper script so the token never appears
    in remote URLs, git config, process args, or git log.
    """
    askpass_script = (
        "#!/bin/sh\n"
        "# GIT_ASKPASS helper — returns the token for HTTPS authentication\n"
        f'printf "%s" "${GITHUB_TOKEN_WAYSEER00}"\n'
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(askpass_script)
        askpass_path = f.name
    os.chmod(askpass_path, 0o700)

    env = {**os.environ, "GIT_ASKPASS": askpass_path, "GIT_TERMINAL_PROMPT": "0"}

    remote_result = subprocess.run(
        ["git", "remote", "get-url", "a0replite"],
        capture_output=True, text=True,
    )
    if remote_result.returncode != 0:
        subprocess.run(["git", "remote", "add", "a0replite", HTTPS_URL], check=True)
    else:
        subprocess.run(["git", "remote", "set-url", "a0replite", HTTPS_URL], check=True)

    push_result = subprocess.run(
        ["git", "push", "a0replite", "main"],
        env=env,
        capture_output=True,
        text=True,
    )
    os.unlink(askpass_path)

    if push_result.returncode != 0:
        print(f"Push failed: {push_result.stderr.replace(token, '***')}")
        sys.exit(1)
    print(f"Pushed to https://github.com/{OWNER}/{REPO_NAME}")


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN_WAYSEER00", "")
    if not token:
        print("Error: GITHUB_TOKEN_WAYSEER00 not set")
        sys.exit(1)
    create_repo(token)
    git_push(token)


if __name__ == "__main__":
    main()

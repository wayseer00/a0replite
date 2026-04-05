from __future__ import annotations

import base64
import time
from typing import Optional

import httpx

_API = "https://api.github.com"
_DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
_CACHE_TTL = 300.0
_file_cache: dict[str, tuple[str, float]] = {}


def _gh_headers(token: str) -> dict:
    return {**_DEFAULT_HEADERS, "Authorization": f"Bearer {token}"}


async def fetch_file(path: str, github_token: str, owner: str = "wayseer00", repo: str = "wayseer.github.io") -> str:
    """
    Fetch a file from a GitHub repo. 5-minute in-process LRU cache.
    Returns decoded file content.
    """
    cache_key = f"{owner}/{repo}/{path}"
    cached = _file_cache.get(cache_key)
    if cached and (time.time() - cached[1]) < _CACHE_TTL:
        return cached[0]

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_gh_headers(github_token),
        )
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

    _file_cache[cache_key] = (content, time.time())
    return content


async def create_gist(content: str, description: str, github_token: str, filename: str = "share.json") -> str:
    """Create a private GitHub Gist. Returns gist_id."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{_API}/gists",
            headers=_gh_headers(github_token),
            json={
                "description": description,
                "public": False,
                "files": {filename: {"content": content}},
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def read_gist(gist_id: str, github_token: str, filename: str) -> str:
    """Read a file from a GitHub Gist. Returns content."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"{_API}/gists/{gist_id}", headers=_gh_headers(github_token))
        resp.raise_for_status()
        return resp.json()["files"][filename]["content"]


async def push_file(
    path: str,
    content: str,
    sha: str,
    github_token: str,
    owner: str = "wayseer00",
    repo: str = "wayseer.github.io",
    commit_message: str = "chore: a0replite patch",
) -> str:
    """Push a file to GitHub. Returns new commit SHA."""
    encoded = base64.b64encode(content.encode()).decode()
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.put(
            f"{_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_gh_headers(github_token),
            json={
                "message": commit_message,
                "content": encoded,
                "sha": sha,
                "committer": {"name": "a0replite", "email": "a0@interdependentway.org"},
            },
        )
        resp.raise_for_status()
        return resp.json()["commit"]["sha"]


async def get_repo_tree(github_token: str, owner: str = "wayseer00", repo: str = "wayseer.github.io") -> list[dict]:
    """Get the full file tree for a repo. Returns list of {path, sha, type}."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        branch_resp = await client.get(
            f"{_API}/repos/{owner}/{repo}",
            headers=_gh_headers(github_token),
        )
        branch_resp.raise_for_status()
        default_branch = branch_resp.json().get("default_branch", "main")

        tree_resp = await client.get(
            f"{_API}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=_gh_headers(github_token),
        )
        tree_resp.raise_for_status()
        return tree_resp.json().get("tree", [])


async def get_default_branch_sha(github_token: str, owner: str = "wayseer00", repo: str = "wayseer.github.io") -> str:
    """Return the latest commit SHA on the default branch."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{_API}/repos/{owner}/{repo}", headers=_gh_headers(github_token))
        resp.raise_for_status()
        default_branch = resp.json().get("default_branch", "main")
        branch_resp = await client.get(
            f"{_API}/repos/{owner}/{repo}/branches/{default_branch}",
            headers=_gh_headers(github_token),
        )
        branch_resp.raise_for_status()
        return branch_resp.json()["commit"]["sha"]

from __future__ import annotations

import base64
import json
from typing import Optional

import httpx

_API = "https://api.github.com"
_HEADERS = {"Accept": "application/vnd.github.v3+json", "X-GitHub-Api-Version": "2022-11-28"}


def _headers_for(token: str) -> dict:
    return {**_HEADERS, "Authorization": f"Bearer {token}"}


async def create_gist(token: str, filename: str, content: str, description: str = "") -> str:
    """Create a private GitHub Gist and return its ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_API}/gists",
            headers=_headers_for(token),
            json={
                "description": description,
                "public": False,
                "files": {filename: {"content": content}},
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def read_gist(token: str, gist_id: str, filename: str) -> str:
    """Read content of a file in a GitHub Gist."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_API}/gists/{gist_id}", headers=_headers_for(token))
        resp.raise_for_status()
        data = resp.json()
        return data["files"][filename]["content"]


async def update_gist(token: str, gist_id: str, filename: str, content: str) -> None:
    """Update a file in an existing Gist."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_API}/gists/{gist_id}",
            headers=_headers_for(token),
            json={"files": {filename: {"content": content}}},
        )
        resp.raise_for_status()


async def store_share(token: str, gist_id: Optional[str], sentinel_id: str, share_b64: str) -> str:
    """Store (or update) a Shamir share in a Gist. Returns the gist_id."""
    filename = f"{sentinel_id}_share.json"
    content = json.dumps({"sentinel": sentinel_id, "share": share_b64}, indent=2)
    if gist_id:
        await update_gist(token, gist_id, filename, content)
        return gist_id
    return await create_gist(token, filename, content, description=f"a0replite share for {sentinel_id}")


async def load_share(token: str, gist_id: str, sentinel_id: str) -> bytes:
    """Load a Shamir share from a Gist and return raw bytes."""
    filename = f"{sentinel_id}_share.json"
    content = await read_gist(token, gist_id, filename)
    data = json.loads(content)
    return base64.b64decode(data["share"])

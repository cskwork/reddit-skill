"""Credential resolution: env vars first, then ~/.claude.json fallback."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import praw

REQUIRED = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD")
USER_AGENT = "cskwork-reddit-mcp/0.1 (by /u/{username})"


@dataclass(frozen=True)
class Creds:
    client_id: str
    client_secret: str
    username: str
    password: str


def _from_env() -> Optional[Creds]:
    if all(os.getenv(k) for k in REQUIRED):
        return Creds(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            username=os.environ["REDDIT_USERNAME"],
            password=os.environ["REDDIT_PASSWORD"],
        )
    return None


def _from_claude_json() -> Optional[Creds]:
    path = Path.home() / ".claude.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for project in (data.get("projects") or {}).values():
        env = ((project.get("mcpServers") or {}).get("reddit") or {}).get("env") or {}
        if all(env.get(k) for k in REQUIRED):
            return Creds(
                client_id=env["REDDIT_CLIENT_ID"],
                client_secret=env["REDDIT_CLIENT_SECRET"],
                username=env["REDDIT_USERNAME"],
                password=env["REDDIT_PASSWORD"],
            )
    return None


def load_creds() -> Creds:
    creds = _from_env() or _from_claude_json()
    if creds is None:
        raise RuntimeError(
            "Reddit credentials not found. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
            "REDDIT_USERNAME, REDDIT_PASSWORD env vars, or configure ~/.claude.json "
            "mcpServers.reddit.env."
        )
    return creds


def reddit_client(creds: Optional[Creds] = None) -> praw.Reddit:
    c = creds or load_creds()
    return praw.Reddit(
        client_id=c.client_id,
        client_secret=c.client_secret,
        username=c.username,
        password=c.password,
        user_agent=USER_AGENT.format(username=c.username),
    )

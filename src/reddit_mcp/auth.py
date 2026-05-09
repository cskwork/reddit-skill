"""Credential resolution: env vars first, then .env, then ~/.claude.json fallback."""
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


def _find_dotenv(start: Optional[Path] = None, max_levels: int = 5) -> Optional[Path]:
    # cwd부터 위로 올라가며 .env 탐색. 루트 또는 max_levels 도달 시 중단.
    here = (start or Path.cwd()).resolve()
    for _ in range(max_levels + 1):
        candidate = here / ".env"
        if candidate.is_file():
            return candidate
        if here.parent == here:
            return None
        here = here.parent
    return None


def _parse_dotenv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (len(value) >= 2) and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def _from_dotenv() -> Optional[Creds]:
    path = _find_dotenv()
    if path is None:
        return None
    try:
        data = _parse_dotenv(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if all(data.get(k) for k in REQUIRED):
        return Creds(
            client_id=data["REDDIT_CLIENT_ID"],
            client_secret=data["REDDIT_CLIENT_SECRET"],
            username=data["REDDIT_USERNAME"],
            password=data["REDDIT_PASSWORD"],
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
    creds = _from_env() or _from_dotenv() or _from_claude_json()
    if creds is None:
        raise RuntimeError(
            "Reddit credentials not found. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
            "REDDIT_USERNAME, REDDIT_PASSWORD as env vars, in a .env file at or above "
            "your current directory, or in ~/.claude.json mcpServers.reddit.env."
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

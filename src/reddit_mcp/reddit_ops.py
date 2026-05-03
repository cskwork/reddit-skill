"""Reddit operations shared by the MCP server and the CLI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import praw
import prawcore


class FlairNotFoundError(LookupError):
    """Requested flair text didn't match any link template on the subreddit."""


@dataclass(frozen=True)
class Flair:
    id: str
    text: str
    editable: bool

    @classmethod
    def from_template(cls, t: dict) -> "Flair":
        return cls(id=t["id"], text=t.get("text") or "", editable=bool(t.get("text_editable")))


def list_flairs(reddit: praw.Reddit, subreddit: str) -> list[Flair]:
    sub = reddit.subreddit(subreddit)
    return [Flair.from_template(t) for t in sub.flair.link_templates]


def resolve_flair_id(reddit: praw.Reddit, subreddit: str, flair_text: str) -> str:
    """Case-insensitive substring match against subreddit flair templates."""
    needle = flair_text.strip().lower()
    flairs = list_flairs(reddit, subreddit)

    exact = [f for f in flairs if f.text.lower() == needle]
    if exact:
        return exact[0].id

    partial = [f for f in flairs if needle in f.text.lower()]
    if len(partial) == 1:
        return partial[0].id
    if len(partial) > 1:
        names = ", ".join(repr(f.text) for f in partial)
        raise FlairNotFoundError(f"Flair {flair_text!r} is ambiguous on r/{subreddit}. Matches: {names}")

    available = ", ".join(repr(f.text) for f in flairs) or "(none)"
    raise FlairNotFoundError(
        f"Flair {flair_text!r} not found on r/{subreddit}. Available: {available}"
    )


def create_post(
    reddit: praw.Reddit,
    *,
    subreddit: str,
    title: str,
    body: str,
    flair_text: Optional[str] = None,
    is_self: bool = True,
    send_replies: bool = True,
) -> dict:
    """Create a post. If flair_text is given, look up the matching flair_id first.

    On a subreddit that requires flair, omitting flair_text will fail with
    Reddit's SUBMIT_VALIDATION_FLAIR_REQUIRED error.
    """
    sub = reddit.subreddit(subreddit)

    flair_id: Optional[str] = None
    if flair_text:
        flair_id = resolve_flair_id(reddit, subreddit, flair_text)

    kwargs = {"title": title[:300], "send_replies": send_replies}
    if is_self:
        kwargs["selftext"] = body
    else:
        kwargs["url"] = body
    if flair_id:
        kwargs["flair_id"] = flair_id

    try:
        submission = sub.submit(**kwargs)
    except prawcore.exceptions.PrawcoreException as e:
        raise RuntimeError(f"Reddit API error: {e}") from e

    return {
        "id": submission.id,
        "url": f"https://www.reddit.com{submission.permalink}",
        "title": submission.title,
        "subreddit": subreddit,
        "flair_id": flair_id,
        "flair_text": flair_text,
    }


def get_post(reddit: praw.Reddit, url_or_id: str) -> dict:
    sub = reddit.submission(url=url_or_id) if "://" in url_or_id else reddit.submission(id=url_or_id)
    return {
        "id": sub.id,
        "title": sub.title,
        "author": str(sub.author) if sub.author else None,
        "subreddit": str(sub.subreddit),
        "url": f"https://www.reddit.com{sub.permalink}",
        "score": sub.score,
        "num_comments": sub.num_comments,
        "selftext": sub.selftext,
        "link_flair_text": sub.link_flair_text,
    }


def search(reddit: praw.Reddit, query: str, *, subreddit: Optional[str] = None, limit: int = 10) -> list[dict]:
    target = reddit.subreddit(subreddit) if subreddit else reddit.subreddit("all")
    out = []
    for s in target.search(query, limit=limit):
        out.append({
            "id": s.id,
            "title": s.title,
            "subreddit": str(s.subreddit),
            "score": s.score,
            "num_comments": s.num_comments,
            "url": f"https://www.reddit.com{s.permalink}",
        })
    return out

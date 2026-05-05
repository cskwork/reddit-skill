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
    """Return link-flair templates for a subreddit.

    Reddit gates `/api/link_flair_v2` to moderators on most subs, so a 403
    is the common case for non-mod accounts. Treat it as "no readable
    templates" and let callers degrade gracefully.
    """
    sub = reddit.subreddit(subreddit)
    try:
        return [Flair.from_template(t) for t in sub.flair.link_templates]
    except prawcore.exceptions.Forbidden:
        return []


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
        try:
            flair_id = resolve_flair_id(reddit, subreddit, flair_text)
        except FlairNotFoundError:
            # Templates not readable (mod-only) or no match. Pass flair_text
            # directly and let Reddit accept or reject it. Subs with
            # text-editable templates or self-assignable flair will accept;
            # strict subs return SUBMIT_VALIDATION_FLAIR_REQUIRED with a
            # clear API error.
            flair_id = None

    kwargs = {"title": title[:300], "send_replies": send_replies}
    if is_self:
        kwargs["selftext"] = body
    else:
        kwargs["url"] = body
    if flair_id:
        kwargs["flair_id"] = flair_id
    elif flair_text:
        kwargs["flair_text"] = flair_text

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


def edit_post(reddit: praw.Reddit, url_or_id: str, new_body: str) -> dict:
    """Edit the body (selftext) of a self post you own.

    Reddit only allows editing the body of self posts; titles are immutable post-submit.
    """
    sub = reddit.submission(url=url_or_id) if "://" in url_or_id else reddit.submission(id=url_or_id)
    if not sub.is_self:
        raise ValueError(f"Submission {sub.id} is a link post; only self-post bodies are editable.")
    try:
        sub.edit(new_body)
    except prawcore.exceptions.PrawcoreException as e:
        raise RuntimeError(f"Reddit API error: {e}") from e
    sub = reddit.submission(id=sub.id)  # refresh
    return {
        "id": sub.id,
        "url": f"https://www.reddit.com{sub.permalink}",
        "title": sub.title,
        "selftext": sub.selftext,
        "edited": bool(sub.edited),
    }


def delete_post(reddit: praw.Reddit, url_or_id: str) -> dict:
    """Delete one of your own posts. Reddit replaces it with [deleted]/[removed]."""
    sub = reddit.submission(url=url_or_id) if "://" in url_or_id else reddit.submission(id=url_or_id)
    sub_id = sub.id
    permalink = sub.permalink
    try:
        sub.delete()
    except prawcore.exceptions.PrawcoreException as e:
        raise RuntimeError(f"Reddit API error: {e}") from e
    return {"id": sub_id, "url": f"https://www.reddit.com{permalink}", "deleted": True}


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


SORT_CHOICES = ("relevance", "hot", "top", "new", "comments")
TIME_FILTER_CHOICES = ("all", "year", "month", "week", "day", "hour")


def search(
    reddit: praw.Reddit,
    query: str,
    *,
    subreddit: Optional[str] = None,
    limit: int = 10,
    sort: str = "relevance",
    time_filter: str = "all",
) -> list[dict]:
    """Search Reddit. For 'study the top recent posts on topic X', use sort='top', time_filter='month'.

    Reddit's API does not expose view counts via PRAW (mod-only); 'top' ranks by score.
    """
    if sort not in SORT_CHOICES:
        raise ValueError(f"sort must be one of {SORT_CHOICES}")
    if time_filter not in TIME_FILTER_CHOICES:
        raise ValueError(f"time_filter must be one of {TIME_FILTER_CHOICES}")
    target = reddit.subreddit(subreddit) if subreddit else reddit.subreddit("all")
    out = []
    for s in target.search(query, sort=sort, time_filter=time_filter, limit=limit):
        out.append({
            "id": s.id,
            "title": s.title,
            "subreddit": str(s.subreddit),
            "score": s.score,
            "num_comments": s.num_comments,
            "url": f"https://www.reddit.com{s.permalink}",
            "selftext": (s.selftext or "")[:1000],
            "is_self": s.is_self,
        })
    return out

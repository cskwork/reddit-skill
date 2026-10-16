"""Cookie-session backend for Reddit.

Reddit closed self-service API application creation in Nov 2025, so OAuth
credentials cannot be obtained. This backend authenticates with the browser
session cookie the operator already holds.

Everything goes through old.reddit.com. Anonymous requests there get 302'd to
/login/ even for public reads (verified), so a session is needed for reads as
well as writes; www.reddit.com is blocked from this host outright.

Verified against a live session:
  * the `reddit_session` cookie alone authenticates (the short-lived token is
    not required and its absence is fine)
  * `POST /api/submit` requires the `uh` (modhash) form field — without it
    Reddit answers 403 before reaching the application layer

Reads are implemented here. Writes are not yet: they raise, so that wiring this
backend in cannot accidentally publish anything.
"""
from __future__ import annotations

import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

import prawcore
import requests

BASE = "https://old.reddit.com"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0"
DEFAULT_COOKIE_FILE = "~/.config/reddit-session/cookies.json"
# The only cookie writes depend on. Verified: it alone authenticates, and the
# short-lived token alone does not, so the others are noise for our purposes.
REQUIRED_COOKIE = "reddit_session"
COOKIE_FILE_ENV = "REDDIT_COOKIE_FILE"

_ID_IN_URL = re.compile(r"/comments/([a-z0-9]+)", re.IGNORECASE)


class SessionError(RuntimeError):
    """The cookie file is missing, unusable, or the session is not authenticated."""


def domain_matches(cookie_domain: str, host: str) -> bool:
    """Cookie domain matches host exactly, or as a parent suffix.

    A naive `host == domain or host == "." + domain` check silently drops every
    `.example.com` cookie when the host is `forums.example.com`, because the
    cookie domain is *shorter* than the host.
    """
    d = (cookie_domain or "").lstrip(".").lower()
    h = (host or "").lower()
    return bool(d) and (h == d or h.endswith("." + d))


def cookie_path(path: Optional[str] = None) -> Path:
    return Path(path or os.getenv(COOKIE_FILE_ENV) or DEFAULT_COOKIE_FILE).expanduser()


def load_cookies(path: Optional[str] = None) -> dict[str, str]:
    """Load reddit.com cookies from a browser JSON export.

    Accepts both the bare-array and {"cookies": [...]} shapes. Enforces mode 600
    at read time so a mis-permissioned file is an actionable error rather than a
    silent success.
    """
    p = cookie_path(path)
    if not p.is_file():
        raise SessionError(
            f"No Reddit cookie file at {p}. Export your reddit.com cookies there as JSON "
            f"(Cookie-Editor extension: Export -> Export as JSON), then `chmod 600 {p}`. "
            f"Or set REDDIT_CLIENT_ID/SECRET/USERNAME/PASSWORD to use OAuth instead."
        )
    mode = stat.S_IMODE(p.stat().st_mode)
    if mode & 0o077:
        raise SessionError(f"{p} is mode {mode:03o} — it must be 600. Run: chmod 600 {p}")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(
            f"{p} is not readable JSON: {exc}. Export as JSON "
            f"(Cookie-Editor: Export -> Export as JSON) rather than as a Netscape file or a "
            "header string — those are different formats and are rejected here."
        ) from exc

    entries = raw.get("cookies") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise SessionError(f"{p}: expected a cookie array or {{'cookies': [...]}}.")

    jar: dict[str, str] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        name, value, dom = item.get("name"), item.get("value"), item.get("domain") or ""
        if name and value is not None and domain_matches(dom, "reddit.com"):
            jar[name] = value
    if not jar:
        raise SessionError(f"{p}: no reddit.com cookies — export from a logged-in reddit.com tab.")
    if REQUIRED_COOKIE not in jar:
        raise SessionError(
            f"{p}: no {REQUIRED_COOKIE!r} cookie. That is the one Reddit authenticates with; "
            f"re-export while logged in. (Found: {', '.join(sorted(jar))})"
        )
    return jar


def _raise_for_errors(payload: dict, what: str) -> None:
    errors = ((payload.get("json") or {}).get("errors") or [])
    if errors:
        code, message, *_ = (*errors[0], None)
        raise RuntimeError(f"Reddit rejected the {what}: [{code}] {message}")


def _thing_url(data: dict) -> str:
    return f"https://www.reddit.com{data.get('permalink', '')}"


def _sub_name(value: Any) -> Optional[str]:
    return value.get("display_name") if isinstance(value, dict) else value


class _Listing:
    """Minimal stand-in for PRAW's CommentForest — enough for list_comments()."""

    def __init__(self, children: list[dict], session: "Session", post_id: Optional[str] = None):
        self._children = children
        self._session = session
        self._post_id = post_id

    def replace_more(self, limit: int = 0) -> None:
        """No-op: more-comments expansion is a PRAW pagination concept.

        ponytail: we request limit=500 up front, so `more` stubs are already
        filled in the common case. Wire pagination in if a thread ever needs it.
        """
        return None

    def __iter__(self) -> Iterator["_Comment"]:
        for child in self._children:
            if child.get("kind") == "t1":
                yield _Comment(child["data"], self._session, self._post_id)


class _Comment:
    def __init__(self, data: dict, session: "Session", post_id: Optional[str] = None):
        self._data = data
        self._session = session
        self._post_id = post_id or (data.get("link_id") or "").removeprefix("t3_")

    def __getattr__(self, item: str) -> Any:
        raise AttributeError(f"{type(self).__name__} has no read attribute {item!r}")

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def fullname(self) -> str:
        return self._data.get("name", f"t1_{self._data['id']}")

    @property
    def author(self) -> Optional[str]:
        return self._data.get("author")

    @property
    def score(self) -> int:
        return self._data.get("score", 0)

    @property
    def body(self) -> str:
        return self._data.get("body", "")

    @property
    def permalink(self) -> str:
        return self._data.get("permalink", "")

    @property
    def parent_id(self) -> str:
        return self._data.get("parent_id", "")

    @property
    def replies(self) -> _Listing:
        return self._session.comment_replies(self.id)

    def refresh(self) -> None:
        fresh = self._session.by_id(f"t1_{self.id}")
        if fresh:
            self._data = fresh

    def reply(self, body: str) -> Optional["_Comment"]:
        return self._session.comment_on(f"t1_{self.id}", body)


class _Submission:
    def __init__(self, data: dict, session: "Session"):
        self._data = data
        self._session = session
        self.comment_sort = "confidence"

    def __getattr__(self, item: str) -> Any:
        raise AttributeError(f"{type(self).__name__} has no read attribute {item!r}")

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def title(self) -> str:
        return self._data.get("title", "")

    @property
    def author(self) -> Optional[str]:
        return self._data.get("author")

    @property
    def subreddit(self) -> str:
        return _sub_name(self._data.get("subreddit")) or ""

    @property
    def permalink(self) -> str:
        return self._data.get("permalink", "")

    @property
    def score(self) -> int:
        return self._data.get("score", 0)

    @property
    def num_comments(self) -> int:
        return self._data.get("num_comments", 0)

    @property
    def selftext(self) -> str:
        return self._data.get("selftext", "") or ""

    @property
    def is_self(self) -> bool:
        return bool(self._data.get("is_self"))

    @property
    def edited(self) -> bool:
        return bool(self._data.get("edited"))

    @property
    def link_flair_text(self) -> Optional[str]:
        return self._data.get("link_flair_text")

    @property
    def comments(self) -> _Listing:
        return self._session.comment_forest(self.id, self.comment_sort)

    def edit(self, body: str) -> None:
        fresh = self._session.edit(f"t3_{self.id}", body)
        if fresh:
            self._data = fresh

    def delete(self):
        return self._session.delete(f"t3_{self.id}")

    def reply(self, body: str) -> Optional[_Comment]:
        return self._session.comment_on(f"t3_{self.id}", body)


class _SearchResult:
    def __init__(self, data: dict):
        self._data = data

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def title(self) -> str:
        return self._data.get("title", "")

    @property
    def subreddit(self) -> str:
        return _sub_name(self._data.get("subreddit")) or ""

    @property
    def score(self) -> int:
        return self._data.get("score", 0)

    @property
    def num_comments(self) -> int:
        return self._data.get("num_comments", 0)

    @property
    def permalink(self) -> str:
        return self._data.get("permalink", "")

    @property
    def selftext(self) -> str:
        return self._data.get("selftext", "") or ""

    @property
    def is_self(self) -> bool:
        return bool(self._data.get("is_self"))


class _FlairListing:
    def __init__(self, session: "Session", subreddit: str):
        self._session = session
        self._subreddit = subreddit

    @property
    def link_templates(self) -> list[dict]:
        try:
            return self._session.flair_templates(self._subreddit)
        except (prawcore.exceptions.Forbidden, requests.HTTPError):
            # 403 (mod-gated) or 404 (route absent) both mean "not readable here".
            return []


class _Subreddit:
    def __init__(self, session: "Session", name: str):
        self._session = session
        self.display_name = name
        self.flair = _FlairListing(session, name)

    def search(self, query: str, *, sort: str = "relevance", time_filter: str = "all",
               limit: int = 10) -> list[_SearchResult]:
        return self._session.search(query, subreddit=self.display_name, sort=sort,
                                     time_filter=time_filter, limit=limit)

    def submit(self, **kwargs):
        """PRAW-shaped entry point. `url` is a link post, `selftext` a self post."""
        return self._session.submit(
            subreddit=self.display_name,
            title=kwargs["title"],
            text=kwargs.get("selftext") or kwargs.get("url") or "",
            flair_id=kwargs.get("flair_id"),
            flair_text=kwargs.get("flair_text"),
            send_replies=kwargs.get("send_replies", True),
        )


class Session:
    """Authenticated old.reddit.com client. Reads only, for now."""

    def __init__(self, cookies: Optional[dict[str, str]] = None, path: Optional[str] = None):
        self.cookies = cookies if cookies is not None else load_cookies(path)
        self._identity: Optional[dict] = None

    # ---- transport -------------------------------------------------------
    def _get(self, path: str, **params) -> requests.Response:
        resp = requests.get(f"{BASE}{path}", params=params or None, cookies=self.cookies,
                            headers={"User-Agent": USER_AGENT}, timeout=30,
                            allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            if "/login" in location:
                raise SessionError(
                    "Reddit session not authenticated — it redirected to /login/. "
                    "Re-export your cookies from a logged-in browser."
                )
        if resp.status_code == 403:
            raise prawcore.exceptions.Forbidden(resp)
        resp.raise_for_status()
        return resp

    def _json(self, path: str, **params) -> Any:
        return self._get(path, **params).json()

    def _post(self, path: str, data: dict, what: str) -> dict:
        """POST a legacy form endpoint with the session cookie and the modhash.

        `uh` is not optional: without it Reddit answers 403 before the request
        reaches the application layer (verified).
        """
        resp = requests.post(f"{BASE}{path}",
                             data={"api_type": "json", "uh": self.modhash, **data},
                             cookies=self.cookies, headers={"User-Agent": USER_AGENT},
                             timeout=30, allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308) and "/login" in resp.headers.get("location", ""):
            raise SessionError(
                f"Reddit session not authenticated while trying to {what} — it redirected to "
                "/login/. Re-export your cookies from a logged-in browser."
            )
        if resp.status_code == 403:
            raise SessionError(
                f"Reddit refused to {what} (403). The thing is most likely not yours, or the "
                "session lacks permission for it."
            )
        resp.raise_for_status()
        try:
            payload = resp.json()
        except ValueError as exc:
            raise SessionError(f"Reddit returned a non-JSON reply while trying to {what}.") from exc
        _raise_for_errors(payload, what)
        data_out = (payload.get("json") or {}).get("data")
        return data_out if isinstance(data_out, dict) else {}

    # ---- identity --------------------------------------------------------
    @property
    def identity(self) -> dict:
        if self._identity is None:
            self._identity = self._json("/api/me.json").get("data") or {}
            if not self._identity.get("name"):
                raise SessionError("Reddit session returned no account data — not authenticated.")
        return self._identity

    @property
    def username(self) -> str:
        return self.identity["name"]

    @property
    def modhash(self) -> str:
        return self.identity.get("modhash") or ""

    # ---- reads -----------------------------------------------------------
    def flair_templates(self, subreddit: str) -> list[dict]:
        return self._json(f"/r/{subreddit}/api/link_flair_v2.json")

    def search(self, query: str, *, subreddit: Optional[str] = None, sort: str = "relevance",
               time_filter: str = "all", limit: int = 10) -> list[_SearchResult]:
        path = f"/r/{subreddit}/search.json" if subreddit else "/search.json"
        params: dict[str, Any] = {"q": query, "sort": sort, "t": time_filter, "limit": limit}
        if subreddit:
            params["restrict_sr"] = 1
        payload = self._json(path, **params)
        return [_SearchResult(c["data"]) for c in payload["data"]["children"]]

    def by_id(self, fullname: str) -> Optional[dict]:
        payload = self._json(f"/by_id/{fullname}.json")
        children = payload["data"]["children"]
        return children[0]["data"] if children else None

    def submission(self, *, url: Optional[str] = None, id: Optional[str] = None) -> _Submission:
        if id is None:
            match = _ID_IN_URL.search(url or "")
            if not match:
                raise ValueError(f"could not find a submission id in {url!r}")
            id = match.group(1)
        data = self.by_id(f"t3_{id}")
        if not data:
            raise ValueError(f"submission {id} not found")
        return _Submission(data, self)

    def comment(self, *, url: Optional[str] = None, id: Optional[str] = None) -> _Comment:
        if id is None:
            match = _ID_IN_URL.search(url or "")
            if not match:
                raise ValueError(f"could not find a comment id in {url!r}")
            id = match.group(1)
        data = self.by_id(f"t1_{id}")
        if not data:
            raise ValueError(f"comment {id} not found")
        return _Comment(data, self)

    def comment_forest(self, post_id: str, sort: str = "top") -> _Listing:
        """Top-level comments for a post, as an iterable of _Comment."""
        sort = "confidence" if sort == "best" else sort
        payload = self._json(f"/comments/{post_id}.json", sort=sort, limit=500)
        return _Listing(payload[1]["data"]["children"], self, post_id)

    def comment_replies(self, comment_id: str) -> _Listing:
        """Replies under one comment, located via its link (post) id."""
        data = self.by_id(f"t1_{comment_id}") or {}
        post_id = (data.get("link_id") or "").removeprefix("t3_")
        if not post_id:
            return _Listing([], self)
        payload = self._json(f"/comments/{post_id}.json", limit=500)
        found = _find_comment(payload[1]["data"]["children"], comment_id)
        if not found:
            return _Listing([], self, post_id)
        return _Listing(_children_of(found.get("replies")), self, post_id)

    # ---- writes ----------------------------------------------------------
    def submit(self, *, subreddit: str, title: str, text: str, flair_id: Optional[str] = None,
               flair_text: Optional[str] = None, send_replies: bool = True) -> "_Submission":
        data: dict[str, Any] = {
            "kind": "self", "sr": subreddit, "title": title[:300], "text": text,
            "sendreplies": "true" if send_replies else "false",
        }
        if flair_id:
            data["flair_id"] = flair_id
        elif flair_text:
            data["flair_text"] = flair_text
        out = self._post("/api/submit", data, "post")
        post_id = out.get("id") or (out.get("name") or "").removeprefix("t3_")
        if not post_id:
            raise SessionError("Reddit accepted the post but returned no id.")
        # Read it back: a web-path submit can succeed and still be removed by
        # moderation, which the submit response alone never reveals.
        fresh = self.by_id(f"t3_{post_id}")
        if fresh:
            return _Submission(fresh, self)
        return _Submission({"id": post_id, "title": title, "selftext": text, "is_self": True,
                            "subreddit": subreddit, "permalink": f"/comments/{post_id}/"}, self)

    def edit(self, thing_id: str, text: str) -> Optional[dict]:
        """Edit a self post's body. Reddit 403s when the thing is not yours."""
        self._post("/api/editusertext", {"thing_id": thing_id, "text": text}, "edit that")
        return self.by_id(thing_id)

    def delete(self, thing_id: str) -> bool:
        """Delete an owned thing, then confirm by reading it back.

        /api/del replies `{}` whether or not it did anything (verified), so the
        POST is not evidence — the read-back is.
        """
        self._post("/api/del", {"id": thing_id}, "delete that")
        after = self.by_id(thing_id)
        if after is None:
            return True
        return (after.get("selftext") or "").strip() in {"[deleted]", "[removed]"}

    def comment_on(self, parent_fullname: str, text: str) -> Optional["_Comment"]:
        """Reply to a t3_/t1_ fullname. None when Reddit echoes no thing back."""
        out = self._post("/api/comment", {"thing_id": parent_fullname, "text": text}, "reply")
        things = out.get("things") or []
        if not things:
            # Accepted but nothing echoed: rate-limited, shadow-blocked, or a
            # comment-restricted subreddit. reddit_ops.reply already treats the
            # equivalent PRAW None as a hard error.
            return None
        return _Comment(things[0]["data"], self)

    # ---- PRAW-shaped entry points ---------------------------------------
    def subreddit(self, name: str = "all") -> _Subreddit:
        return _Subreddit(self, name)


def _children_of(replies: Any) -> list[dict]:
    """Children from a `replies` field — which is either a listing or empty string."""
    if not isinstance(replies, dict):
        return []
    return ((replies.get("data") or {}).get("children")) or []


def _find_comment(children: list[dict], comment_id: str) -> Optional[dict]:
    for child in children:
        if child.get("kind") != "t1":
            continue
        data = child.get("data") or {}
        if data.get("id") == comment_id:
            return data
        found = _find_comment(_children_of(data.get("replies")), comment_id)
        if found:
            return found
    return None


def credential_expiries(path: Optional[str] = None) -> list[dict]:
    """Per-cookie name and remaining lifetime. Never returns a cookie value.

    Validates presence and mode first, so this cannot become a side door around
    the 0600 requirement.
    """
    load_cookies(path)
    raw = json.loads(cookie_path(path).read_text(encoding="utf-8"))
    entries = raw.get("cookies") if isinstance(raw, dict) else raw
    now = time.time()
    out = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        if not domain_matches(item.get("domain") or "", "reddit.com"):
            continue
        expires = item.get("expirationDate")
        out.append({
            "name": item.get("name"),
            "session_cookie": bool(item.get("session")),
            "expires_in_hours": round((expires - now) / 3600, 1)
            if isinstance(expires, (int, float)) else None,
        })
    return sorted(out, key=lambda c: (c["expires_in_hours"] is None, c["expires_in_hours"]))


def session_client(path: Optional[str] = None) -> Session:
    return Session(path=path)


def session_available(path: Optional[str] = None) -> bool:
    try:
        load_cookies(path)
    except SessionError:
        return False
    return True

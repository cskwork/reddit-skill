# Reddit session-cookie auth — verified endpoint facts

Companion to the `browser-session-auth` skill, which carries the general procedure.
These are the Reddit-specific details that took real probing to establish, so a
future session does not re-derive them. Reddit closed self-service API app creation,
so a new client id cannot be obtained and the browser session is the only route.

## Hosts

| Host | Anonymous behaviour | Use |
|---|---|---|
| `old.reddit.com` | `302` → `/login/?reason=…&dest=<your target>` on **every** path, `.json` ones included | The host to use |
| `www.reddit.com` | `403` from this host | Prefer the legacy host; still worth re-probing, as host behaviour changes |

The `dest=` parameter echoing your own target back is the signal that the endpoint is
live and merely auth-gated. There is no credential-free read path — reads need the
session as much as writes do.

## Credentials

- Cookie file: `~/.config/reddit-session/cookies.json`, mode `600`. Override with
  `REDDIT_COOKIE_FILE`.
- Producing it: install the **Cookie-Editor** extension
  ([cookie-editor.com](https://cookie-editor.com/); Chrome, Firefox, Safari, Edge, iOS), open
  `reddit.com` **while logged in**, then **Export → Export as JSON** and save that to the path
  above. Take the *JSON* option specifically — Cookie-Editor also offers Netscape and header-string
  exports, which are different formats and are rejected.
- Both JSON shapes are accepted: a bare array, or `{"cookies": [...]}`.
- **The `reddit_session` cookie alone authenticates**, and it lives roughly six months.
- The short-lived token (`token_v2`, ~24 h) alone returns `302` and is **not** required.
  Do not design a daily re-export cadence around it.
- Anti-bot cookies in the same jar (`loid`, `edgebucket`, `session_tracker`, `csv`, …)
  are noise: they are minted per IP/fingerprint and are not what authenticates you.

## Requirements per operation

| Operation | Endpoint | Needs |
|---|---|---|
| identity + modhash | `GET /api/me.json` | session cookie |
| flair templates | `GET /r/<sub>/api/link_flair_v2.json` | session cookie; the `.json` suffix is required or it `404`s |
| search | `GET /r/<sub>/search.json?q=…&restrict_sr=1` | session cookie |
| post / comment data | `GET /comments/<id>.json`, `GET /by_id/t3_<id>.json` | session cookie |
| submit a self post | `POST /api/submit` | session cookie **and** `uh=<modhash>` |
| edit a self post body | `POST /api/editusertext` | as above; `403` when the thing is not yours |
| delete an owned thing | `POST /api/del` | as above; replies `{}` either way — **confirm by reading back** |
| reply to a post/comment | `POST /api/comment` | as above; empty `data.things` means it did **not** take (rate-limit / shadow-block) |

`uh` is mandatory on writes. The identical request without it returns `403`, which
reads as "not authenticated" while you are in fact authenticated. Fetch the modhash
from `/api/me.json` on each run rather than caching it across sessions.

Identity payload: `data.name` is the username, `data.modhash` is the token.

## Probing a write without writing

Post to `/api/submit` targeting a subreddit that cannot exist. A JSON error body
(`[["SUBREDDIT_NOEXIST", …]]`) proves the request was authenticated and validated at
the application layer, and nothing is created — validation rejects the target before
any write occurs.

## Flair

Flair `text` comes back HTML-escaped (`Memory &amp; Context`). Unescape before
matching it against the label shown on screen, or the match silently fails. Templates
are readable with an ordinary session on most subs, so flair resolution does not need
moderator rights — a `403` or `404` here just means "not readable", which callers
should degrade on rather than raise.

## Markdown

Post bodies are Reddit-flavoured Markdown with several silent-failure modes. See
`reddit-markdown.md` in this same directory, and run `scripts/reddit_post_check.py`
over any body before submitting it.

"""FastMCP server exposing flair-aware Reddit tools."""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import reddit_ops
from .auth import reddit_client

mcp = FastMCP("reddit-mcp")


@mcp.tool()
def list_flairs(subreddit: str) -> list[dict]:
    """List link-post flair templates available on a subreddit.

    Args:
        subreddit: Subreddit name without the r/ prefix.
    """
    flairs = reddit_ops.list_flairs(reddit_client(), subreddit)
    return [{"id": f.id, "text": f.text, "editable": f.editable} for f in flairs]


@mcp.tool()
def create_post(
    subreddit: str,
    title: str,
    body: str,
    flair_text: Optional[str] = None,
    is_self: bool = True,
) -> dict:
    """Create a Reddit post. Resolves flair_text to the matching flair_id automatically.

    Args:
        subreddit: Subreddit name without r/ prefix.
        title: Post title (truncated to 300 chars).
        body: Post body (markdown for self posts, URL for link posts).
        flair_text: Display text of the flair to attach; matched case-insensitively
            (exact first, then unique substring). Required on subreddits that enforce flair.
        is_self: True for text post, False for link post.

    Returns:
        Dict with id, url, title, subreddit, flair_id, flair_text.
    """
    return reddit_ops.create_post(
        reddit_client(),
        subreddit=subreddit,
        title=title,
        body=body,
        flair_text=flair_text,
        is_self=is_self,
    )


@mcp.tool()
def edit_post(url_or_id: str, new_body: str) -> dict:
    """Edit the body of one of your own self posts. Title cannot be changed."""
    return reddit_ops.edit_post(reddit_client(), url_or_id, new_body)


@mcp.tool()
def delete_post(url_or_id: str) -> dict:
    """Delete one of your own posts."""
    return reddit_ops.delete_post(reddit_client(), url_or_id)


@mcp.tool()
def get_post(url_or_id: str) -> dict:
    """Fetch a single submission by URL or ID."""
    return reddit_ops.get_post(reddit_client(), url_or_id)


@mcp.tool()
def reply(target: str, body: str, kind: Optional[str] = None) -> dict:
    """Reply to a Reddit post (top-level comment) or to a comment.

    Args:
        target: Reddit URL, fullname (`t1_xxx` for comment, `t3_xxx` for post),
            or bare ID. URLs and fullnames are auto-detected. Bare IDs default
            to submission; pass `kind="comment"` to override.
        body: Reply body in markdown.
        kind: Force interpretation as "post" or "comment". Default: auto-detect.

    Returns:
        Dict with id, fullname, url, parent_id, body, replied_to, parent_url.
    """
    return reddit_ops.reply(reddit_client(), target, body, kind=kind)


@mcp.tool()
def search_reddit(
    query: str,
    subreddit: Optional[str] = None,
    limit: int = 10,
    sort: str = "relevance",
    time_filter: str = "all",
) -> list[dict]:
    """Search Reddit. Restrict to one subreddit by passing subreddit; otherwise searches r/all.

    For style-matching ("show me top recent posts on topic X in r/Y"), use
    sort='top' and time_filter='month' (or 'week' for fresher).

    Args:
        query: Search query.
        subreddit: Limit search to this subreddit. Default: r/all.
        limit: Max results, 1-100.
        sort: One of relevance|hot|top|new|comments.
        time_filter: One of all|year|month|week|day|hour. Used by sort='top' and 'controversial'.
    """
    return reddit_ops.search(
        reddit_client(), query, subreddit=subreddit, limit=limit, sort=sort, time_filter=time_filter,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

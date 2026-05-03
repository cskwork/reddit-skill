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
def get_post(url_or_id: str) -> dict:
    """Fetch a single submission by URL or ID."""
    return reddit_ops.get_post(reddit_client(), url_or_id)


@mcp.tool()
def search_reddit(query: str, subreddit: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Search Reddit. Restrict to one subreddit by passing subreddit; otherwise searches r/all."""
    return reddit_ops.search(reddit_client(), query, subreddit=subreddit, limit=limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

"""Standalone CLI for posting/listing without the MCP transport. Usable as `reddit-post`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import reddit_ops
from .auth import reddit_client


def _read_body(arg: str | None, body_file: str | None) -> str:
    if body_file:
        return Path(body_file).read_text(encoding="utf-8")
    if arg is not None:
        return arg
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --body, --body-file, or pipe text via stdin.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reddit-post", description="Post to Reddit with flair support.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_post = sub.add_parser("post", help="Create a self post.")
    p_post.add_argument("--subreddit", required=True)
    p_post.add_argument("--title", required=True)
    p_post.add_argument("--body")
    p_post.add_argument("--body-file", help="Read body from this file path.")
    p_post.add_argument("--flair", help="Flair display text (case-insensitive match).")
    p_post.add_argument("--dry-run", action="store_true", help="Resolve flair and print plan without posting.")

    p_flairs = sub.add_parser("flairs", help="List available flair templates for a subreddit.")
    p_flairs.add_argument("subreddit")

    p_get = sub.add_parser("get", help="Fetch a post by URL or ID.")
    p_get.add_argument("url_or_id")

    p_edit = sub.add_parser("edit", help="Edit the body of one of your own self posts.")
    p_edit.add_argument("url_or_id")
    p_edit.add_argument("--body")
    p_edit.add_argument("--body-file")

    p_del = sub.add_parser("delete", help="Delete one of your own posts.")
    p_del.add_argument("url_or_id")

    p_reply = sub.add_parser(
        "reply",
        help="Reply to a post (top-level comment) or to a comment.",
    )
    p_reply.add_argument(
        "target",
        help="Reddit URL, fullname (t1_/t3_), or bare ID. Bare IDs default to submission.",
    )
    p_reply.add_argument("--body")
    p_reply.add_argument("--body-file", help="Read body from this file path.")
    p_reply.add_argument(
        "--kind",
        choices=["post", "comment"],
        help="Force interpretation. Default: auto-detect from URL/fullname.",
    )
    p_reply.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve target and print plan without replying.",
    )

    p_search = sub.add_parser(
        "search",
        help="Search posts. For style-matching, use --sort top --time-filter month.",
    )
    p_search.add_argument("query")
    p_search.add_argument("--subreddit")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--sort", default="relevance",
                          choices=["relevance", "hot", "top", "new", "comments"])
    p_search.add_argument("--time-filter", default="all",
                          choices=["all", "year", "month", "week", "day", "hour"])

    p_comments = sub.add_parser("comments", help="List a post's comments (with ids) for replying.")
    p_comments.add_argument("ref", help="Post or comment URL, fullname (t1_/t3_), or bare ID.")
    p_comments.add_argument("--sort", default="top",
                            choices=["best", "top", "new", "controversial", "old"])
    p_comments.add_argument("--limit", type=int, default=50)
    p_comments.add_argument("--kind", choices=["post", "comment"],
                            help="Force interpretation. Default: auto-detect from ref.")

    args = parser.parse_args(argv)
    reddit = reddit_client()

    if args.cmd == "flairs":
        flairs = reddit_ops.list_flairs(reddit, args.subreddit)
        if not flairs:
            print(f"r/{args.subreddit} has no link-post flair templates (or you can't read them).")
            return 0
        for f in flairs:
            print(f"{f.id}\t{f.text!r}\teditable={f.editable}")
        return 0

    if args.cmd == "get":
        print(json.dumps(reddit_ops.get_post(reddit, args.url_or_id), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "edit":
        body = _read_body(args.body, args.body_file)
        print(json.dumps(reddit_ops.edit_post(reddit, args.url_or_id, body), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "delete":
        print(json.dumps(reddit_ops.delete_post(reddit, args.url_or_id), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "reply":
        body = _read_body(args.body, args.body_file)
        replied_to = args.kind or (
            "comment" if reddit_ops._looks_like_comment_target(args.target) else "post"
        )
        if args.dry_run:
            print(json.dumps({
                "would_reply": {
                    "target": args.target,
                    "replied_to": replied_to,
                    "body_chars": len(body),
                }
            }, indent=2, ensure_ascii=False))
            return 0
        result = reddit_ops.reply(reddit, args.target, body, kind=args.kind)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "search":
        results = reddit_ops.search(
            reddit, args.query,
            subreddit=args.subreddit, limit=args.limit,
            sort=args.sort, time_filter=args.time_filter,
        )
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "comments":
        result = reddit_ops.list_comments(
            reddit, args.ref, sort=args.sort, limit=args.limit, kind=args.kind,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "post":
        body = _read_body(args.body, args.body_file)
        if args.dry_run:
            flair_id = None
            if args.flair:
                try:
                    flair_id = reddit_ops.resolve_flair_id(reddit, args.subreddit, args.flair)
                except reddit_ops.FlairNotFoundError:
                    # Templates not readable or no match; real post will
                    # fall back to passing flair_text directly to Reddit.
                    flair_id = None
            print(json.dumps({
                "would_post": {
                    "subreddit": args.subreddit,
                    "title": args.title,
                    "body_chars": len(body),
                    "flair_text": args.flair,
                    "resolved_flair_id": flair_id,
                }
            }, indent=2, ensure_ascii=False))
            return 0
        result = reddit_ops.create_post(
            reddit,
            subreddit=args.subreddit,
            title=args.title,
            body=body,
            flair_text=args.flair,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

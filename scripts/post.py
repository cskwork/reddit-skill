"""Thin wrapper so `uv run scripts/post.py ...` works without installing the entry point.

Equivalent to `reddit-post` once the package is installed.
"""
from reddit_mcp.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

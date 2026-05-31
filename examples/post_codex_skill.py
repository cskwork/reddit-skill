"""Dogfood: post the claude-codex-skill announcement to r/ClaudeCode with flair.

Usage:
    uv run examples/post_codex_skill.py --flair Showcase
    uv run examples/post_codex_skill.py --flair Showcase --dry-run
"""
from __future__ import annotations

import argparse
import json

from reddit_mcp import reddit_ops
from reddit_mcp.auth import reddit_client

SUBREDDIT = "ClaudeCode"
TITLE = "/codex-cli skill — call Codex from Claude Code for review, impl, or image-gen (no OPENAI_API_KEY)"
BODY = """Single skill, three subcommands:

- **`/codex-cli review`** — `codex review` on the diff, regrouped CRITICAL/HIGH/MEDIUM/LOW with `file:line` cites.
- **`/codex-cli impl "<task>"`** — sandboxed `codex exec -s workspace-write`. No `danger-full-access` without explicit per-run OK.
- **`/codex-cli image "<prompt>"`** — uses Codex's built-in `image_gen.imagegen`. Auths via `codex login` (ChatGPT). **No `OPENAI_API_KEY`.** Trick: don't tell Codex to "use the OpenAI API" or it shells out instead. Skill also handles the Windows `CreateProcessAsUserW failed: 5` copy bug by grabbing the PNG from `~/.codex/generated_images/`.

**Repo:** https://github.com/cskwork/claude-codex-skill — MIT, single `SKILL.md`, install one-liner, reproducible test suite.

Needs Claude Code + `codex >= 0.128` + `codex login`.

*Posted via my own Reddit skill (https://github.com/cskwork/reddit-skill) at my request.*
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flair", default="Showcase",
                        help="Flair display text. Defaults to 'Showcase'. Use `reddit-post flairs ClaudeCode` to discover.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    reddit = reddit_client()

    if args.dry_run:
        flair_id = reddit_ops.resolve_flair_id(reddit, SUBREDDIT, args.flair)
        print(json.dumps({
            "would_post": {
                "subreddit": SUBREDDIT,
                "title": TITLE,
                "body_chars": len(BODY),
                "flair_text": args.flair,
                "resolved_flair_id": flair_id,
            }
        }, indent=2, ensure_ascii=False))
        return 0

    result = reddit_ops.create_post(
        reddit,
        subreddit=SUBREDDIT,
        title=TITLE,
        body=BODY,
        flair_text=args.flair,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

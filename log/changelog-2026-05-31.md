# Changelog 2026-05-31

## feat: comment listing (`comments` CLI command + `get_comments` MCP tool)

### Why
Replying to a specific commenter needs that comment's `t1_` thing_id, but the
toolkit had no way to discover it: the CLI only had
`post/flairs/get/edit/delete/reply/search`, the MCP server had no
comment-listing tool, and fetching `reddit.com/...json` is blocked in some
sandboxes. The only workaround was dropping to raw PRAW. This closes the gap so
"reply to comments on my post" no longer requires manual permalink copying.

### Changes
- `reddit_ops.py`: new `list_comments(reddit, ref, sort, limit, kind)`. Returns
  `{post_id|comment_id, sort, count, comments[]}` where each comment carries
  `id`, `thing_id` (`t1_...`, ready for `reply`), `author`, `score`, and a
  280-char body snippet. Reuses `_looks_like_comment_target`, `_extract_id`,
  `_load_submission`. `sort="best"` maps to Reddit's `confidence`. `kind`
  forces post-vs-comment; otherwise auto-detected from `ref`.
- `cli.py`: new `comments <ref>` subcommand (`--sort`, `--limit`, `--kind`).
- `server.py`: new `get_comments` MCP tool wrapping the same function.
- `skills/reddit-poster/SKILL.md`: "Finding a comment id first" subsection under
  Replying.

### Verification
- `ast.parse` clean on cli.py / server.py / reddit_ops.py.
- `reddit-post --help` lists `comments`.
- E2E: `reddit-post comments 1to6gt2 --sort new` returned real ids
  (`t1_onyu531`/InfinriDev, `t1_oo0ajw5`/KamaSamaa) matching the live thread.
- No automated tests added: the repo currently has no test suite, so this was
  verified by live run rather than fabricating a test layout. Adding a pytest
  suite is a separate follow-up.

spent an hour trying to post a project on r/ClaudeAI through the popular reddit MCP server and kept hitting the same wall — Reddit's API rejected every submission with "post must contain post flair" and the MCP didn't expose a flair parameter at all. checked a couple of alternatives, found one that takes a `flair` arg but passes it to PRAW where Reddit actually expects a `flair_id`, so the flair silently drops and the post fails the same way.

so i built a small one that does the lookup correctly: pass `flair_text="Showcase"`, the server fetches `subreddit.flair.link_templates`, matches by display text (case-insensitive, exact first then unique substring), and submits with the resolved id. errors come back with the full list of valid flairs so you know what to retry with.

tools over MCP: `create_post`, `edit_post`, `delete_post`, `list_flairs`, `get_post`, `search_reddit`. there's also a standalone CLI (`reddit-post post|edit|delete|flairs|get`) for one-off use without the MCP transport, and a bundled claude code skill that encodes a four-step flow — discover flairs, draft body, dry-run, post with explicit user approval.

credentials read from env vars first, then `~/.claude.json` `mcpServers.reddit.env` as fallback, so it slots into existing configs without re-entering secrets.

repo (MIT, python + PRAW + FastMCP): https://github.com/cskwork/reddit-skill

happy to take feedback or PRs — especially if your sub uses flair conventions i haven't tested against.

(this post was made using the MCP itself, which felt like the appropriate dogfood test.)

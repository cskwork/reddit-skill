# reddit-mcp

Reddit MCP server with **proper post-flair support**, plus a standalone CLI/PRAW poster. Built because the popular Reddit MCP servers either don't expose `flair_id` at all or pass the flair text where Reddit's API expects an ID.

- **MCP tools**: `create_post` (with case-insensitive flair lookup), `edit_post`, `delete_post`, `reply`, `list_flairs`, `get_post`, `search_reddit`
- **CLI**: `reddit-post post|flairs|get|edit|delete|reply|search` for one-off use without an MCP client
- **Auth**: env vars first, then `~/.claude.json`'s `mcpServers.reddit.env` as fallback

## Install

```bash
git clone https://github.com/cskwork/reddit-mcp
cd reddit-mcp
uv sync
```

## Credentials

Set these env vars (or rely on `~/.claude.json` fallback):

```
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USERNAME
REDDIT_PASSWORD
```

Get the client id/secret from <https://www.reddit.com/prefs/apps> by creating a "script" app. If your account has 2FA, generate an app password instead of using your account password.

## Use as a CLI

```bash
# Discover what flairs r/ClaudeCode requires
uv run reddit-post flairs ClaudeCode

# Dry run — resolve flair id and print the plan without posting
uv run reddit-post post --subreddit ClaudeCode \
  --title "My new tool" --body "Body in markdown" --flair Showcase --dry-run

# Real post
uv run reddit-post post --subreddit ClaudeCode \
  --title "My new tool" --body-file notes.md --flair Showcase
```

`stdin` works too: `cat notes.md | uv run reddit-post post --subreddit X --title Y --flair Z`.

### Reply to a post or comment

```bash
# Reply to a post (top-level comment) — auto-detected from a submission URL
uv run reddit-post reply https://www.reddit.com/r/X/comments/POST_ID/slug/ \
  --body-file reply.md --dry-run

# Reply to a specific comment — auto-detected from a comment URL
uv run reddit-post reply https://www.reddit.com/r/X/comments/POST_ID/slug/COMMENT_ID/ \
  --body "thanks for the question — short answer is..."

# Force interpretation when passing a bare ID (defaults to post otherwise)
uv run reddit-post reply abc123 --body "..." --kind comment
```

Returns `{id, fullname, url, parent_id, body, replied_to, parent_url}`. If Reddit accepts the request but returns no comment (rate-limit or shadow-block), the call raises with a clear message instead of silently succeeding.

## Use as an MCP server (Claude Code / Claude Desktop)

Add to your MCP config (e.g. `~/.claude.json` `mcpServers`):

```json
{
  "reddit": {
    "type": "stdio",
    "command": "uv",
    "args": ["--directory", "/absolute/path/to/reddit-mcp", "run", "reddit-mcp"],
    "env": {
      "REDDIT_CLIENT_ID": "...",
      "REDDIT_CLIENT_SECRET": "...",
      "REDDIT_USERNAME": "...",
      "REDDIT_PASSWORD": "..."
    }
  }
}
```

Restart Claude Code. Seven tools become available: `create_post`, `edit_post`, `delete_post`, `reply`, `list_flairs`, `get_post`, `search_reddit`.

## Claude Code skill — `reddit-poster`

A bundled skill at [`skills/reddit-poster/SKILL.md`](skills/reddit-poster/SKILL.md) teaches Claude how to use these tools well: discover flairs first, draft in a human (lowercase, story-first) style instead of marketing copy, dry-run before posting, follow Reddit's Responsible Builder Policy on disclosure, and stop for explicit user approval before any irreversible action (post, edit, delete).

Install:

```bash
# Windows
mkdir "$env:USERPROFILE\.claude\skills\reddit-poster"
copy skills\reddit-poster\SKILL.md "$env:USERPROFILE\.claude\skills\reddit-poster\SKILL.md"

# macOS / Linux
mkdir -p ~/.claude/skills/reddit-poster
cp skills/reddit-poster/SKILL.md ~/.claude/skills/reddit-poster/SKILL.md
```

Then restart Claude Code and ask to post on Reddit; the skill loads automatically.

### `create_post(subreddit, title, body, flair_text=None, is_self=True)`

If the subreddit requires flair, pass `flair_text` — the server fetches `subreddit.flair.link_templates`, matches by display text (exact first, then unique substring, case-insensitive), and submits with the resolved `flair_id`. If the match is ambiguous or missing, you get back the list of valid flairs in the error.

## Why this exists

The widely shipped Reddit MCP servers fail two ways:

1. **No flair param at all** → can't post to subreddits that require flair (most large communities).
2. **Flair param accepted but mishandled** → the text is passed where Reddit expects an ID, silently dropping the flair or failing validation.

This server does the lookup correctly: text in, ID resolved, post submitted.

## Responsible Builder Policy

This server respects [Reddit's Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy):

- Don't post identical content across subreddits — use it for one place at a time, rewrite per audience.
- Don't manipulate votes, karma, or send unsolicited DMs.
- Disclose bot/automation when posting on behalf of an LLM.

## License

MIT — see [LICENSE](LICENSE).

# reddit-skill

A Reddit **CLI** (`reddit-post`) for posting with **proper flair handling**, with an optional MCP server on the side. Built because the popular Reddit MCP servers either don't expose `flair_id` at all or pass the flair text where Reddit's API expects an ID.

- **CLI** (primary): `reddit-post post|flairs|get|edit|delete|reply|search` — all features, no MCP client required.
- **MCP server** (optional): same tools exposed over stdio for Claude Code / Claude Desktop.
- **Skill**: bundled `reddit-poster` Claude skill that wraps the CLI in a discover → draft → dry-run → approve flow.

## Install

```bash
git clone https://github.com/cskwork/reddit-mcp
cd reddit-mcp
uv sync
```

## Credentials

Resolution order: **env vars → `.env` (walked up from cwd) → `~/.claude.json` `mcpServers.reddit.env` (fallback)**.

The recommended setup is a `.env` at your project (or repo) root:

```bash
cp .env.example .env
# then edit .env with your values
```

`.env` keys (all required):

```
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USERNAME
REDDIT_PASSWORD
```

Get the client id/secret from <https://www.reddit.com/prefs/apps> by creating a "script" app. If your account uses 2FA, generate an app password instead of using your account password. `.env` is already in `.gitignore`.

The `~/.claude.json` fallback exists for backward compatibility with users who already configured Reddit credentials inside an MCP block — it keeps working, but new setups should prefer `.env`.

## CLI

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

### Edit and delete

Reddit only allows editing the **body** of self posts, not the title.

```bash
uv run reddit-post edit <url> --body-file new_body.md
uv run reddit-post delete <url>
```

Title-only changes require delete + repost. The original URL dies; warn anyone with inbound links before doing this.

## Optional: use as an MCP server

If you prefer to call these tools from Claude Code / Claude Desktop's MCP integration instead of the CLI, add this to your MCP config (e.g. `~/.claude.json` `mcpServers`):

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

The MCP path is functionally equivalent to the CLI — same package, same PRAW under the hood, same flair resolution. Choose based on where you want to call from.

### `create_post(subreddit, title, body, flair_text=None, is_self=True)`

If the subreddit requires flair, pass `flair_text` — the server fetches `subreddit.flair.link_templates`, matches by display text (exact first, then unique substring, case-insensitive), and submits with the resolved `flair_id`. If the match is ambiguous or missing, you get back the list of valid flairs in the error.

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

Then restart Claude Code and ask to post on Reddit; the skill loads automatically and drives the CLI.

## Why this exists

The widely shipped Reddit MCP servers fail two ways:

1. **No flair param at all** → can't post to subreddits that require flair (most large communities).
2. **Flair param accepted but mishandled** → the text is passed where Reddit expects an ID, silently dropping the flair or failing validation.

This package does the lookup correctly: text in, ID resolved, post submitted. The CLI is the primary surface because most users only need a tool that posts; the MCP wrapper is there for those who want it inside Claude's tool-use loop.

## Responsible Builder Policy

This package respects [Reddit's Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy):

- Don't post identical content across subreddits — use it for one place at a time, rewrite per audience.
- Don't manipulate votes, karma, or send unsolicited DMs.
- Disclose bot/automation when posting on behalf of an LLM.

## License

MIT — see [LICENSE](LICENSE).

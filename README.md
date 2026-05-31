# reddit-skill

A Claude **skill** (`reddit-poster`) for posting to Reddit the way a careful human would: discover the sub's flair and conventions, draft in a story-first style instead of marketing copy, dry-run, and stop for your approval before anything irreversible. Under the hood it's a Reddit **CLI** (`reddit-post`) with **proper flair handling** — built because the popular Reddit MCP servers either don't expose `flair_id` at all or pass the flair text where Reddit's API expects an ID.

- **Skill** (primary): the bundled `reddit-poster` Claude skill runs a discover → draft → dry-run → approve flow so posts read human and land with the right flair.
- **CLI**: `reddit-post post|flairs|get|edit|delete|reply|comments|search` — the engine the skill calls; works standalone too, no MCP client required.
- **MCP server** (optional): the same tools over stdio, for people who prefer the MCP transport over the skill.

## Install

```bash
git clone https://github.com/cskwork/reddit-skill
cd reddit-skill
uv sync
```

## Claude Code skill — `reddit-poster` (the main way to use this)

The bundled skill at [`skills/reddit-poster/SKILL.md`](skills/reddit-poster/SKILL.md) is the recommended entry point. It teaches Claude to post like a person, not a bot: discover flairs and read the sub's top posts first, draft in a human (lowercase, story-first) style instead of marketing copy, dry-run before posting, follow Reddit's Responsible Builder Policy on disclosure, and stop for explicit user approval before any irreversible action (post, edit, delete).

Install:

```bash
# Windows
mkdir "$env:USERPROFILE\.claude\skills\reddit-poster"
copy skills\reddit-poster\SKILL.md "$env:USERPROFILE\.claude\skills\reddit-poster\SKILL.md"

# macOS / Linux
mkdir -p ~/.claude/skills/reddit-poster
cp skills/reddit-poster/SKILL.md ~/.claude/skills/reddit-poster/SKILL.md
```

Then restart Claude Code and ask to post on Reddit; the skill loads automatically and drives the CLI for you — you mostly review drafts and approve the live submit.

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

## CLI (the engine the skill drives)

You can also call the CLI directly for one-off use without the skill:

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

### List comments (to find an id to reply to)

`reply` needs a comment's URL or `t1_` id, but a bare post URL doesn't hand those out. List them first:

```bash
# Top-level comments of a post: id, thing_id (t1_, ready for reply), author, score, body
uv run reddit-post comments <post-url-or-id> --sort new --limit 50

# Replies under a specific comment instead of a post's top level
uv run reddit-post comments <comment-url-or-id> --kind comment
```

Take a `thing_id` straight to `reddit-post reply <t1_id> --kind comment`.

### Edit and delete

Reddit only allows editing the **body** of self posts, not the title.

```bash
uv run reddit-post edit <url> --body-file new_body.md
uv run reddit-post delete <url>
```

Title-only changes require delete + repost. The original URL dies; warn anyone with inbound links before doing this.

## Optional: use as an MCP server

If you'd rather call these tools from Claude Code / Claude Desktop's MCP integration than use the skill or CLI, add this to your MCP config (e.g. `~/.claude.json` `mcpServers`):

```json
{
  "reddit": {
    "type": "stdio",
    "command": "uv",
    "args": ["--directory", "/absolute/path/to/reddit-skill", "run", "reddit-mcp"],
    "env": {
      "REDDIT_CLIENT_ID": "...",
      "REDDIT_CLIENT_SECRET": "...",
      "REDDIT_USERNAME": "...",
      "REDDIT_PASSWORD": "..."
    }
  }
}
```

Restart Claude Code. Eight tools become available: `create_post`, `edit_post`, `delete_post`, `reply`, `get_comments`, `list_flairs`, `get_post`, `search_reddit`.

The MCP path is functionally equivalent to the CLI — same package, same PRAW under the hood, same flair resolution. The skill is still the recommended way in because it adds the discover-and-draft discipline the raw tools don't; MCP just changes where the tools are called from.

### `create_post(subreddit, title, body, flair_text=None, is_self=True)`

If the subreddit requires flair, pass `flair_text` — the server fetches `subreddit.flair.link_templates`, matches by display text (exact first, then unique substring, case-insensitive), and submits with the resolved `flair_id`. If the match is ambiguous or missing, you get back the list of valid flairs in the error.

## Why this exists

Two problems, one package:

1. **Posting like a bot.** Most tooling makes it trivial to dump marketing copy into a sub and get removed (or downvoted) for it. The `reddit-poster` skill encodes the discipline a careful poster uses — read the room first, draft story-first, disclose, get approval — so the output reads human.
2. **Broken flair handling.** The widely shipped Reddit MCP servers either expose no flair param at all (can't post to subs that require flair — most large communities), or accept a flair param but pass the text where Reddit expects an ID, silently dropping it. This package does the lookup correctly: text in, ID resolved, post submitted.

The skill is the primary surface; the CLI is the engine underneath; the MCP wrapper is there for those who want it inside Claude's tool-use loop.

## Responsible Builder Policy

This package respects [Reddit's Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy):

- Don't post identical content across subreddits — use it for one place at a time, rewrite per audience.
- Don't manipulate votes, karma, or send unsolicited DMs.
- Disclose bot/automation when posting on behalf of an LLM.

## License

MIT — see [LICENSE](LICENSE).

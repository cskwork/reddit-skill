---
name: reddit-poster
description: Draft and publish Reddit posts that read human (lowercase, story-first) using the cskwork/reddit-mcp tools, with flair lookup, dry-run, and Reddit Responsible Builder Policy compliance.
when_to_use: User asks to "post on Reddit", "share this on r/X", "advertise on Reddit", or invokes /reddit-poster. Also when editing or deleting their own posts, or replying to a post or comment.
allowed-tools: Bash(uv *) Bash(reddit-post *) Read Write
---

Wrap the `cskwork/reddit-mcp` toolkit so Claude can take a project, repo, or idea and publish a Reddit post that doesn't read like marketing copy. Drives the **`reddit-post` CLI** (primary path — works in any session regardless of MCP loading state). The same package also exposes MCP tools (`create_post`, `edit_post`, `delete_post`, `reply`, `list_flairs`, `get_post`, `search_reddit`) if the user prefers; both call the same PRAW core.

Repo: <https://github.com/cskwork/reddit-mcp>

## Verify once per session

```bash
uv --version       # 0.4+ recommended
cd <path-to-reddit-mcp> && uv run reddit-post --help
```

If credentials missing, the CLI raises with the exact env vars to set. Resolution order: env vars → `.env` (walked up from cwd) → `~/.claude.json` `mcpServers.reddit.env` fallback.

## The four-step flow

Every Reddit post follows this loop. Don't skip steps.

1. **Discover** — list flairs **and** pull the top 5 most-upvoted recent posts on the relevant topic in the target sub.
2. **Draft** — write a human-style body that matches what you saw in step 1, show it to the user, iterate.
3. **Dry-run** — confirm flair resolution and length before going live.
4. **Post** — get explicit user approval, then `create_post`.

### Step 1 — discover

Pick exactly one subreddit. Cross-posting identical content violates Reddit Responsible Builder Policy and the MCP itself blocks it.

#### 1a. Flairs

```bash
uv run reddit-post flairs <subreddit>
```

If the sub requires flair, you'll see them. If it has none, the CLI says so. Pick a flair that matches the post type (Showcase / Project / Discussion / Help — varies by sub).

#### 1b. Top 5 recent posts on the relevant topic (mandatory)

This grounds your draft in the actual community's conventions, not a generic "human" template. Pick a query that captures the topic of what you're posting (the project's category, not its name — you want comparable posts, not your own past activity).

```bash
uv run reddit-post search "<topic keywords>" \
  --subreddit <name> --sort top --time-filter month --limit 5
```

Read the returned `title`, `selftext`, `score`, and `num_comments`. Extract:

- **Title shape** — sentence case vs Title Case, length, punctuation, emoji use
- **Opening line** — anecdote vs question vs claim vs spec
- **Body length** — most subs have a strong norm (short paragraph vs essay)
- **Formatting density** — bullet/bold use, code block frequency
- **Disclosure or self-promo style** — how others handle "i made this"

Then make your draft match that register. If the top 5 are all 200-word personal stories, don't ship a 1,500-word feature list. If they're all spec sheets with bullet lists, lean into that. The "lowercase casual" default in step 2 is overridden by what the sub actually rewards.

If you find no relevant top posts (very small sub, narrow topic), drop time_filter to `year` or `all`, or fall back to the default style rules in step 2.

PRAW does not expose Reddit's view counts (mod-only data), so "top" ranks by score (net upvotes), which is the closest proxy.

### Step 2 — draft (the human-style rules)

The post must read like a person sharing something they built, not a landing page. Apply what you observed in step 1b — the rules below are defaults, not overrides.

- **Open with a personal moment, not a feature list.** "got tired of jumping between two terminals…" beats "Single skill, three subcommands:". Lead with the pain or the trigger.
- **Default to lowercase, casual sentences.** Reserve capitals for proper nouns and code identifiers.
- **No TL;DR, no heavy bold, no emoji, no marketing adjectives.** Skip "powerful", "blazing", "seamless", "easy-to-use".
- **Bullet lists are allowed but sparing.** One tight list of two or three items. Never the whole post.
- **Acknowledge limitations honestly.** Edge cases and known bugs in line, not buried at the bottom.
- **End with a low-key invitation.** "happy to take questions or feedback" — not "smash that upvote".
- **Code references inline with backticks.** No code blocks unless the snippet is non-trivial.
- **Keep title plain, but capitalize it.** The body is lowercase casual; the **title is not**. Use sentence case at minimum (first letter capital, proper nouns capital, rest natural). Title Case is fine for short titles. All-lowercase titles read as either careless or affected and most subs penalize them. Reddit titles are immutable post-submit; triple-check before submitting.

### Step 3 — dry-run

Always dry-run. Confirms flair resolves, shows the body byte count, surfaces title issues.

```bash
uv run reddit-post post \
  --subreddit <name> \
  --title "<title>" \
  --body-file draft.md \
  --flair "<Flair Text>" \
  --dry-run
```

If flair resolution fails, the error lists every available flair. Pick one and retry.

### Step 4 — post (with explicit user approval)

Show the user the resolved plan from the dry-run, then ask for explicit go-ahead. **Do not auto-submit.** Posting is an irreversible external action.

```bash
uv run reddit-post post \
  --subreddit <name> \
  --title "<title>" \
  --body-file draft.md \
  --flair "<Flair Text>"
```

Returns `{id, url, title, subreddit, flair_id, flair_text}`. Verify by re-fetching:

```bash
uv run reddit-post get <url>
```

Confirm `link_flair_text` matches what you intended — that's the only way to be sure flair landed.

## Replying to a post or comment

Use `reply` to leave a top-level comment on a submission, or to respond to a specific comment.

```bash
# Reply to a post (auto-detected from submission URL)
uv run reddit-post reply <post_url> --body-file reply.md --dry-run
uv run reddit-post reply <post_url> --body-file reply.md

# Reply to a comment (auto-detected from comment URL)
uv run reddit-post reply <comment_url> --body "..."

# Bare IDs default to submission — pass --kind comment to override
uv run reddit-post reply abc123 --body "..." --kind comment
```

Replies follow the same human-style rules as posts (lowercase casual, no marketing tone), but shorter. A reply that runs longer than the comment it answers usually loses readers — match the length of the question, not the length of your codebase.

Always dry-run first to confirm the target is interpreted as expected (`replied_to: "post"` vs `"comment"`). Get explicit user approval before the live submit; replies are also irreversible external actions.

## Editing and deleting

Reddit allows editing the **body** of self posts, not the title.

```bash
uv run reddit-post edit <url> --body-file new_body.md
```

Title-only changes require **delete + repost**. Get explicit user approval before either:

```bash
uv run reddit-post delete <url>
uv run reddit-post post --subreddit <name> --title <new> ...
```

Risks of delete + repost:

- The original URL dies (broken inbound links from elsewhere).
- Reddit may flag the repost as spam if the body is identical and timing is close. If the original had engagement (>1 score, any comments), warn the user before deleting.

## Disclosure (Reddit Responsible Builder Policy)

Reddit's [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) requires bot-generated content to clearly disclose its automated nature.

- "Bot-generated" includes posts where an LLM drafted the body, even if the human approved.
- The policy-safe form is a one-line italic disclosure at the bottom: *posted via my own Reddit MCP — https://github.com/cskwork/reddit-mcp*
- If the user asks to omit the disclosure, **flag the policy conflict once** ("technically this triggers the bot-disclosure rule and risks moderator action"), then comply with the user's call. The user owns the account and the consequences.
- Never silently drop the disclosure to make a post look more organic. Always surface the choice.

## What not to do

- **Don't cross-post.** One subreddit per piece of content. Different sub? Rewrite the body for that audience.
- **Don't manipulate votes or karma.** Don't ask people to upvote, don't post the same thing from multiple accounts, don't brigade.
- **Don't DM users.** The MCP doesn't expose DM tools and shouldn't.
- **Don't post without the user's go-ahead on the live submit step.** Drafts are free; submissions cost trust.
- **Don't paste the user's secrets, internal docs, or unreleased code into a public post.** Re-confirm with the user if any content looks sensitive.

## When the slash command is invoked

If the user types `/reddit-poster` with a description of what they want posted, infer the subreddit from context (their previous request, the project's audience). If unclear, ask once. Then run the four-step flow above and stop at step 4 for explicit approval.

If the user types `/reddit-poster edit <url> ...` or `/reddit-poster delete <url>`, route to the edit/delete flow above.

## Output discipline

- Don't dump raw CLI output. Summarize: post URL, title, flair, score/comments after verification.
- For drafts, show the rendered body in a fenced markdown block so the user can preview formatting.
- For errors (flair not found, auth missing, spam detection), show the actionable fix, not the stack trace.

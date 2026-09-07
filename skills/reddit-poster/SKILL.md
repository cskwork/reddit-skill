---
name: reddit-poster
description: Draft, preview, publish, reply to, edit, or delete Reddit content using the reddit-post CLI, with subreddit-rule checks, flair validation, and explicit authorization for live changes.

---


# reddit-poster

Wrap the `cskwork/reddit-skill` toolkit so Claude can take a project, repo, or idea and publish a Reddit post that doesn't read like marketing copy. Drives the **`reddit-post` CLI** as the primary path (works in any session regardless of MCP loading state); the same tools are also exposed as optional MCP tools (`create_post`, `edit_post`, `delete_post`, `reply`, `list_flairs`, `get_post`, `search_reddit`) for those who prefer that transport.

Repo: <https://github.com/cskwork/reddit-skill>

## Verify once per session

```bash
uv --version       # 0.4+ recommended
cd <path-to-reddit-skill> && uv run reddit-post --help
```

If credentials missing, the CLI raises with the exact env vars to set. Resolution order: env vars → `.env` walked up from cwd (the recommended setup) → `~/.claude.json`'s `mcpServers.reddit.env` fallback.

## The four-step flow

Every Reddit post follows this loop. Don't skip steps.

1. **Discover** — list flairs **and** pull the top 5 most-upvoted recent posts on the relevant topic in the target sub.
2. **Draft** — write a human-style body that matches what you saw in step 1, show it to the user, iterate.
3. **Dry-run** — confirm flair resolution and length before going live.
4. **Post** — get explicit user approval, then `reddit-post post`.

### Step 1 — discover

Pick exactly one subreddit. Cross-posting identical content violates Reddit Responsible Builder Policy and the toolkit itself blocks it.

#### 1.0. Account-level gate (mandatory before step 1a)

Use these conservative toolkit defaults for self-promotion, not as claimed Reddit platform limits:

- At most two owned-product/repo posts per rolling 24 hours across all subreddits.
- Wait 24 hours between self-promotional posts to the same subreddit.
- After a moderator removal, use a one-post cap for the next 24 hours and check whether the community requires a megathread.

The toolkit has no account-history command. Use known session activity and ask only for missing recent history; do not infer a count. State the count and applicable limit before proceeding. If the limit is reached, hold the post and report when it can be reconsidered.

#### 1.1. Sub-rules check (mandatory before flairs)

Read the target subreddit's current rules/sidebar in the browser before drafting. Do not use `gh api` for Reddit; it addresses GitHub. Look for any of:

- "no self-promotion" / "no advertising"
- "showcases go in the weekly thread"
- "submissions require X% non-self-promo karma"
- Megathread-only language: "use the [stickied/weekly/monthly] thread"

If the sub is megathread-only for self-promo, skip the post flow entirely. Find the current megathread (sub's pinned posts, or search "megathread" / "showcase" / "what are you working on") and use the `reply` flow instead (see "Replying to a post or comment" below). Do not substitute a top-level post when the rules require a comment.

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

Use these editorial length defaults, adjusted to the community evidence from step 1b:

- **Showcase / project share**: 120-200 words. Hard ceiling 250.
- **Tutorial / explainer**: 200-400 words. Hard ceiling 500.
- **Bug report / help request**: as short as the question allows.
- **Personal essay / take**: 400-800 words only if the top 1-3 posts in step 1b are that long. Otherwise cut.

If your draft is over the target, the right move is almost always cutting, not condensing further with the same ideas. Pick the one or two things that actually matter and delete the rest. Specificity beats coverage — one concrete number ("355 skills, 55 used") beats a paragraph of generalities.

The other rules:

- **Say what the thing does within the first three sentences.** A hook is fine, but by sentence three a stranger must be able to answer "what is this?" in plain words. Real comment that prompted this rule: "Can you write this in human so I can understand what it does better?" If the reader has to reach the middle of the post to learn what the tool is, the post failed no matter how good the prose is.
- **Open with a personal moment or a concrete number, not a feature list.** "got tired of jumping between two terminals…" beats "Single skill, three subcommands:". Lead with the pain, the trigger, or a surprising data point.
- **Default to lowercase, casual sentences.** Reserve capitals for proper nouns and code identifiers.
- **No TL;DR, no heavy bold, no emoji, no marketing adjectives.** Skip "powerful", "blazing", "seamless", "easy-to-use".
- **At most one bullet list, three or four items.** Never the whole post. If you're listing more than four items, you're padding.
- **Acknowledge limitations honestly but tersely.** One line, in the body, not a "known limits" section. Long limits sections read as defensive and add length without adding value.
- **End with a low-key invitation in one short sentence.** "curious what your X looks like" or "happy to take feedback". Not "smash that upvote", not a multi-line outro.
- **Code references inline with backticks.** No code blocks unless the snippet is non-trivial. One install snippet is enough; don't add a quickstart, an "advanced usage", and a "configuration" block in the same post.
- **Keep title plain, but capitalize it.** The body is lowercase casual; the **title is not**. Use sentence case at minimum (first letter capital, proper nouns capital, rest natural). Title Case is fine for short titles. Reddit titles are immutable post-submit; verify the final title before submitting.

**AI-tell audit (mandatory, before showing the user).** Well-crafted prose can still scream LLM. After the length check, reread the draft asking "what makes this obviously AI-written?" and fix these tells:

- **"not X, but Y" / "X, not Y" framings.** "contracts, not headcount", "a liability, not an asset", "bound to bytes, not to memory". One per post at most; zero is better. Stacked, they are the single loudest LLM tell.
- **Aphorisms and slogan lines.** If a sentence would work on a conference slide, rewrite it as a plain statement of what happens.
- **Triadic repetition and twist endings.** "I wrote it. I reviewed it. I never saw it." Every paragraph landing on a punchline is machine cadence. Vary rhythm; let most sentences just end.
- **Em dashes.** Periods or commas instead.
- **Uniform paragraph shape.** Humans write a one-line paragraph next to a five-line one.
- **Abstract manifesto before concrete mechanism.** Cut the philosophy paragraph; keep the anecdote and what the tool actually does.

Fix the affected passages; rewrite the whole draft only when its structure causes the problem.

Length check: count words. If over the ceiling, cut whole ideas, then run the AI-tell audit again on what remains. Only then show the user.

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

### Finding a comment id first

`reply` needs the comment's URL or id, but a bare post URL doesn't hand you per-comment ids, and fetching `reddit.com/...json` is blocked in some sandboxes. When you only have the post and want to answer specific commenters, list ids first:

```bash
# id | thing_id (t1_xxx) | author | score | body snippet, for every top-level comment
uv run reddit-post comments <post_url|id> --sort new --limit 50
# replies under one comment instead of a post's top level:
uv run reddit-post comments <comment_url|id> --kind comment
```

Take the `thing_id` (`t1_...`) straight to `reply <thing_id> --kind comment` or the MCP `reply` tool. The MCP `get_comments` tool returns the same fields if you prefer that path.

```bash
# Reply to a post (auto-detected from submission URL)
uv run reddit-post reply <post_url> --body-file reply.md --dry-run
uv run reddit-post reply <post_url> --body-file reply.md

# Reply to a comment (auto-detected from comment URL)
uv run reddit-post reply <comment_url> --body "..."

# Bare IDs default to submission — pass --kind comment to override
uv run reddit-post reply abc123 --body "..." --kind comment
```

Replies follow the same human-style rules and AI-tell audit as posts (lowercase casual, no marketing tone), but shorter. A reply that runs longer than the comment it answers usually loses readers — match the length of the question, not the length of your codebase.

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

## Disclosure and app transparency

Check the current [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) and subreddit rules. The policy checked on 2026-09-08 requires app registration/profile labeling, prohibits circumvention of Reddit labeling, and bans automated spam including substantially similar cross-subreddit content. It does not prescribe the footer below or define every human-approved LLM draft as a bot post.

When a footer is useful or required by the community, disclose the actual tool used, for example *posted with reddit-post*. Do not call a CLI submission an MCP submission or imply that a footer substitutes for platform labeling or access approval. Retain required disclosures; discuss optional wording with the user.

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

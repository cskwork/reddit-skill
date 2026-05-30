# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/), and the project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-05-31

### Added
- **Comment listing.** New `reddit-post comments <post_url|id>` CLI subcommand and `get_comments` MCP tool to list a post's top-level comments (or a comment's replies via `--kind comment`). Each entry returns `id`, `thing_id` (`t1_...`, ready to pass to `reply`), `author`, `score`, and a body snippet. Closes the gap where replying to a specific commenter required dropping to raw PRAW. (`reddit_ops.list_comments`)

## [0.1.0]

### Added
- Flair-aware Reddit MCP server and `reddit-post` CLI: `post`, `flairs`, `get`, `edit`, `delete`, `reply`, `search`.
- Flair resolution by display text (case-insensitive, exact then unique substring) to Reddit's required `flair_id`.
- Reddit Responsible Builder Policy guidance baked into the `reddit-poster` skill.

[0.2.0]: https://github.com/cskwork/reddit-skill/releases/tag/v0.2.0
